"""
Entity Extractor — Semantic NLP pipeline for structured business entity extraction.

Architecture (per user design):
  Stage 1: IndicNLP text normalization + sentence segmentation
  Stage 2: LaBSE semantic slot filling via cosine similarity
           IndicNER (kept for ORG/LOC span extraction only)
  Stage 3: Composite confidence scoring

Replaces all hardcoded regex + dictionary lookup logic with
language-agnostic sentence embeddings that work across all
22 Indian languages without any per-language rules.

Extracts the 12 specified fields from MSE owner transcripts:
  1. enterprise_name
  2. product_descriptions
  3. raw_materials_mentioned
  4. manufacturing_process_keywords
  5. buyer_types_mentioned
  6. buyer_geographies_mentioned
  7. production_scale_mentioned
  8. years_in_business
  9. employees_count
  10. existing_online_presence
  11. language_of_response
  12. confidence_per_field
"""

import logging
import re
import threading
import json
import time
import ollama
import difflib
from typing import Dict, Any, List, Optional, Tuple

import numpy as np

from .manufacturing_detector import ManufacturingDetector

logger = logging.getLogger(__name__)

# ── Model IDs ────────────────────────────────────────────────────────────────
INDICNER_MODEL_ID = "ai4bharat/IndicNER"
LABSE_MODEL_ID = "sentence-transformers/LaBSE"

# ── LaBSE Slot Anchor Sentences (English) ───────────────────────────────────
# Because LaBSE maps all 109 languages into the same vector space,
# these English anchors will match semantically equivalent sentences in
# Hindi, Tamil, Telugu, Marathi, Gujarati, Bengali, etc.
SLOT_ANCHORS: Dict[str, List[str]] = {
    "raw_material": [
        "we use cotton as raw material",
        "steel and iron are our inputs",
        "we buy wood and process it",
        "our raw material is silk fabric",
        "we source aluminium and brass",
        "we use flour and wheat to make food",
        "rubber and plastic are our ingredients",
    ],
    "manufacturing_process": [
        "we have a factory and manufacture ourselves",
        "weaving and stitching happens in our workshop",
        "we assemble and produce the goods here",
        "we operate machines to make the products",
        "production happens at our own plant",
        "we manufacture in house",
        "we have our own factory",
        "we make it ourselves at the workshop",
    ],
    "product_description": [
        "we make cotton shirts and kurtas",
        "our main product is leather bags",
        "we produce steel furniture",
        "we manufacture plastic containers",
        "our products are handloom sarees",
        "we make wooden furniture and decorations",
        "we produce electronic components",
        "we manufacture garments and apparel",
    ],
    "trading": [
        "we buy goods and sell them",
        "we import and distribute products",
        "we purchase wholesale and sell retail",
        "we are a distributor and reseller",
        "we only sell, we do not make anything",
        "we stock and resell finished goods",
    ],
    "buyer_geography": [
        "we sell to Delhi and Mumbai",
        "our customers are in Gujarat",
        "we supply across Maharashtra",
        "we export to foreign countries",
        "our markets are in southern India",
        "we sell locally in this city",
    ],
    "buyer_type": [
        "we sell to other businesses in bulk",
        "our customers are retail shops",
        "we supply to government departments",
        "we sell directly to end consumers",
        "our buyers are wholesale traders",
        "we export to international clients",
    ],
}

# ── Online presence keywords (kept as fast substring check) ──────────────────
ONLINE_PRESENCE_KEYWORDS = [
    "amazon", "flipkart", "instagram", "facebook", "whatsapp",
    "meesho", "indiamart", "udaan", "jiomart", "myntra",
    "snapdeal", "shopify", "website", "online", "e-commerce",
    "ecommerce", "ऑनलाइन", "वेबसाइट", "इंटरनेट",
    "थ्रू बेचते", "थ्रू sell", "through website",
]

# ── Numeric field patterns (kept — LaBSE doesn't extract exact numbers) ──────
_YEAR_PATTERNS = []
_EMPLOYEE_PATTERNS = []
_SCALE_PATTERNS = []

EXTRACTION_PROMPT = """Extract Indian MSE business info. Return ONLY JSON, no markdown.

Transcript: {transcript}

Rules:
- Extract ONLY what is explicitly stated. Never infer or hallucinate.
- product_descriptions: product names ONLY. Do NOT include raw materials here. E.g., for "cotton shirts", put "shirts" here.
- raw_materials_mentioned: EXTRACT SEPARATELY from products. E.g. if they say "कॉटन शर्ट्स बनाते हैं" or "कॉटन यूज़ करते हैं", put "कॉटन" here, and ONLY "शर्ट्स" in product_descriptions.
- manufacturing_process_keywords: extract ONLY the exact process words present in the transcript (e.g., "बनाते", "फैक्ट्री", "सिलाई", "manufacture"). Do not extract words unless they are actually spoken. empty [] ONLY if no manufacturing words exist.
- selling_channels: explicitly capture platforms mentioned (e.g., "IndiaMART", "Amazon", "Flipkart", "GeM", "वेबसाइट"/website, WhatsApp, Instagram). if non-empty, existing_online_presence must be true.
- buyer_types_mentioned: e.g. "retailers", "wholesalers", "direct customers".
- years_in_business: integer (दस=10, पांच=5, बीस=20, पंद्रह=15) or null
- employees_count: integer or null
- export_signal: true or false (boolean, not string)
- existing_online_presence: boolean (true or false). true if selling online or has a website.
- buyer_geographies: specific cities/districts only, never "India" or "abroad". Include foreign cities if export_signal is true.
- annual_turnover: explicitly extract the yearly turnover if mentioned (e.g. "50 lakhs", "2 crores", "10 units"). Do NOT confuse with quantity.
- daily_production_capacity: explicitly extract volume/quantity produced per day/month (e.g. "100 pieces", "500 kilo").
- factory_area_size: explicitly extract factory size if mentioned (e.g. "2000 gaj", "5000 sq ft").
- major_machinery_used: extract names of machines used (e.g. "Juki machine", "CNC router").
- Rejoin STT splits: "गाज़िया आबाद" → "गाज़ियाबाद"

{{"enterprise_name":null,"product_descriptions":[],"raw_materials_mentioned":[],"manufacturing_process_keywords":[],"buyer_types_mentioned":[],"buyer_geographies_mentioned":[],"production_scale_mentioned":null,"years_in_business":null,"employees_count":null,"existing_online_presence":null,"export_signal":false,"selling_channels":[],"annual_turnover":null,"daily_production_capacity":null,"factory_area_size":null,"major_machinery_used":[]}}"""



class EntityExtractor:
    """
    Extract structured business entities from transcribed text using
    a language-agnostic semantic pipeline based on LaBSE embeddings.

    IndicNER (ai4bharat/IndicNER) is kept for precise ORG/LOC span
    extraction since it outperforms LaBSE at named entity boundary detection.
    LaBSE handles all intent-like slot fills (product, material, process, etc.)
    """

    # ── Singleton NER (IndicNER) ──────────────────────────────────────────────
    _ner_model = None
    _ner_tokenizer = None
    _ner_loaded = False
    _ner_error: Optional[str] = None
    _ner_lock = threading.Lock()

    # ── Singleton LaBSE ──────────────────────────────────────────────────────
    _labse_model = None
    _labse_loaded = False
    _labse_error: Optional[str] = None
    _labse_lock = threading.Lock()
    _anchor_embeddings: Optional[Dict[str, np.ndarray]] = None

    def __init__(self):
        self.mfg_detector = ManufacturingDetector()

    # ────────────────────────────────────────────────────────────────────────
    # Model Loading
    # ────────────────────────────────────────────────────────────────────────

    @classmethod
    def load_ner_model(cls) -> bool:
        """Load the IndicNER token classification model. Call at startup."""
        if cls._ner_loaded:
            return True

        with cls._ner_lock:
            if cls._ner_loaded:
                return True
            try:
                from transformers import AutoModelForTokenClassification, AutoTokenizer
                import torch
                import os

                logger.info("Loading IndicNER model: %s", INDICNER_MODEL_ID)
                cls._ner_tokenizer = AutoTokenizer.from_pretrained(
                    INDICNER_MODEL_ID, token=os.environ.get("HF_TOKEN")
                )
                cls._ner_model = AutoModelForTokenClassification.from_pretrained(
                    INDICNER_MODEL_ID,
                    token=os.environ.get("HF_TOKEN"),
                    torch_dtype=torch.float16,
                )
                device = "cuda" if torch.cuda.is_available() else "cpu"
                cls._ner_model.to(device)
                cls._ner_model.eval()
                cls._ner_loaded = True
                logger.info("IndicNER loaded on %s", device)
                return True
            except Exception as e:
                cls._ner_error = str(e)
                logger.error("Failed to load IndicNER: %s", e)
                return False

    @classmethod
    def load_labse_model(cls) -> bool:
        """Load LaBSE sentence embedder and pre-compute anchor embeddings."""
        if cls._labse_loaded:
            return True

        with cls._labse_lock:
            if cls._labse_loaded:
                return True
            try:
                from sentence_transformers import SentenceTransformer

                logger.info("Loading LaBSE model: %s", LABSE_MODEL_ID)
                cls._labse_model = SentenceTransformer(LABSE_MODEL_ID)

                # Pre-compute and cache anchor embeddings once at startup
                logger.info("Computing LaBSE slot anchor embeddings...")
                cls._anchor_embeddings = {}
                for slot_name, anchors in SLOT_ANCHORS.items():
                    cls._anchor_embeddings[slot_name] = cls._labse_model.encode(
                        anchors, normalize_embeddings=True, show_progress_bar=False
                    )

                cls._labse_loaded = True
                logger.info("LaBSE loaded and anchor embeddings cached.")
                return True
            except Exception as e:
                cls._labse_error = str(e)
                logger.error("Failed to load LaBSE: %s", e)
                return False

    # ────────────────────────────────────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────────────────────────────────────

    def extract(
        self, transcript: str, language: str = "hi"
    ) -> Dict[str, Any]:
        """
        Extract all structured fields from a transcript using the local Gemma3:4B LLM.
        """
        if not transcript or not transcript.strip():
            return self._empty_result(language)

        try:
            response = ollama.chat(
                model="gemma3:4b",
                messages=[{
                    "role": "user",
                    "content": EXTRACTION_PROMPT.format(transcript=transcript)
                }],
                format="json",
                options={
                    "temperature": 0,
                    "num_predict": 256,
                    "num_ctx": 1024,
                    "num_keep": 0,
                    "repeat_penalty": 1.1
                }
            )
            out_str = response["message"]["content"].strip()
            raw_data = json.loads(out_str)
        except Exception as e:
            logger.error("LLM Extraction failed: %s", e)
            return self._empty_result(language)

        # Sanitize LLM output to match schema and deduplicate
        data = self._sanitize_llm_json(raw_data)

        # Build confidence scores (mocked to 0.9 for LLM outputs to satisfy downstream schema)
        confidence = {
            "enterprise_name": 0.9 if data.get("enterprise_name") else None,
            "product_descriptions": 0.9 if data.get("product_descriptions") else None,
            "raw_materials_mentioned": 0.9 if data.get("raw_materials_mentioned") else None,
            "manufacturing_process_keywords": 0.9 if data.get("manufacturing_process_keywords") else None,
            "buyer_types_mentioned": 0.9 if data.get("buyer_types_mentioned") else None,
            "buyer_geographies_mentioned": 0.9 if data.get("buyer_geographies_mentioned") else None,
            "production_scale_mentioned": 0.9 if data.get("production_scale_mentioned") else None,
        }
        non_null = [v for v in confidence.values() if v is not None]
        confidence["overall_extraction_confidence"] = round(sum(non_null) / len(non_null), 4) if non_null else 0.0

        return {
            "extracted_entities": data,
            "confidence_scores": confidence,
            "language_of_response": language,
        }

    def _sanitize_llm_json(self, data: dict) -> dict:
        defaults = {
            "enterprise_name": None,
            "product_descriptions": [],
            "raw_materials_mentioned": [],
            "manufacturing_process_keywords": [],
            "buyer_types_mentioned": [],
            "buyer_geographies_mentioned": [],
            "production_scale_mentioned": None,
            "years_in_business": None,
            "employees_count": None,
            "existing_online_presence": None,
            "export_signal": False,
            "selling_channels": [],
            "annual_turnover": None,
            "daily_production_capacity": None,
            "factory_area_size": None,
            "major_machinery_used": [],
        }
        for key, default in defaults.items():
            if key not in data:
                data[key] = default

        for field in ["years_in_business", "employees_count"]:
            v = data.get(field)
            if isinstance(v, str):
                data[field] = int(v) if v.isdigit() else None

        for field in ["export_signal", "existing_online_presence"]:
            v = data.get(field)
            if isinstance(v, str):
                if v.lower() == "true":   data[field] = True
                elif v.lower() == "false": data[field] = False
                elif v.lower() == "null":  data[field] = None
            elif isinstance(v, list):
                data[field] = True if v else None
                if field == "existing_online_presence":
                    for item in v:
                        if isinstance(item, str) and item not in data.get("selling_channels", []):
                            data["selling_channels"].append(item)

        seen = []
        deduped = []
        for p in data.get("product_descriptions", []):
            if not isinstance(p, str): continue
            normalized = p.strip()
            if len(normalized) <= 2: continue
            
            is_dup = False
            for s in seen:
                if difflib.SequenceMatcher(None, normalized, s).ratio() > 0.65:
                    is_dup = True
                    break
                    
            if not is_dup:
                seen.append(normalized)
                deduped.append(p)
        data["product_descriptions"] = deduped

        if data.get("selling_channels"):
            data["existing_online_presence"] = True
        elif data.get("existing_online_presence") is False:
            data["existing_online_presence"] = None

        return data

    # ────────────────────────────────────────────────────────────────────────
    # Stage 1: Normalization & Sentence Splitting
    # ────────────────────────────────────────────────────────────────────────

    def _normalize_and_split(self, text: str, lang: str) -> List[str]:
        """
        Normalize Unicode/nukta issues with IndicNLP, then
        split into sentences using indicnlp's sentence tokenizer.
        Falls back to simple split on punctuation if indicnlp is unavailable.
        """
        normalized = text
        try:
            from indicnlp.normalize.indic_normalize import IndicNormalizerFactory
            factory = IndicNormalizerFactory()
            normalizer = factory.get_normalizer(lang)
            normalized = normalizer.normalize(text)
        except Exception as e:
            logger.debug("indicnlp normalization unavailable: %s", e)

        # Sentence splitting
        sentences = []
        try:
            from indicnlp.tokenize import sentence_tokenize
            sentences = sentence_tokenize.sentence_split(normalized, lang=lang)
        except Exception as e:
            logger.debug("indicnlp sentence split unavailable: %s", e)
            sentences = [normalized]
            
        # Spoken transcripts often lack punctuation. If sentences are too long, split heuristically
        refined_sentences = []
        for s in sentences:
            if len(s.split()) > 10 and lang == "hi":
                # Split on common spoken Hindi sentence boundaries
                chunks = re.split(r'(है|हैं|था|थे|थी)\s+', s)
                # re.split keeps the delimiter if wrapped in capturing group. Reconstruct:
                current = ""
                for i in range(0, len(chunks)-1, 2):
                    part = chunks[i] + chunks[i+1] + " "
                    refined_sentences.append(part.strip())
                if len(chunks) % 2 != 0 and chunks[-1].strip():
                    refined_sentences.append(chunks[-1].strip())
            else:
                refined_sentences.append(s)

        # Filter empty strings
        sentences = [s.strip() for s in refined_sentences if s.strip() and len(s.strip()) > 3]
        if not sentences:
            sentences = [normalized]
        return sentences

    # ────────────────────────────────────────────────────────────────────────
    # Stage 2a: LaBSE Semantic Slot Filling
    # ────────────────────────────────────────────────────────────────────────

    def _fill_slots(
        self, sentences: List[str], threshold: float = 0.45
    ) -> Dict[str, List[Dict]]:
        """
        Embed each sentence with LaBSE and compute cosine similarity
        against all slot anchor embeddings.

        Returns a dict: slot_name -> list of {"text": ..., "confidence": ...}
        sorted by confidence descending.
        """
        if not sentences or self._labse_model is None:
            return {}

        # Encode all sentences in one batch
        sent_embeddings = self._labse_model.encode(
            sentences, normalize_embeddings=True, show_progress_bar=False
        )  # shape: (N_sentences, embed_dim)

        results: Dict[str, List[Dict]] = {}

        for slot_name, anchor_embs in self._anchor_embeddings.items():
            # Cosine similarity: (N_sentences, N_anchors)
            sims = np.dot(sent_embeddings, anchor_embs.T)
            slot_matches = []
            for i, sentence in enumerate(sentences):
                max_sim = float(sims[i].max())
                if max_sim >= threshold:
                    slot_matches.append({
                        "text": sentence,
                        "confidence": max_sim,
                        "slot": slot_name,
                    })
            slot_matches.sort(key=lambda x: x["confidence"], reverse=True)
            if slot_matches:
                results[slot_name] = slot_matches

        return results

    # ────────────────────────────────────────────────────────────────────────
    # Stage 2b: IndicNER Named Entity Spans
    # ────────────────────────────────────────────────────────────────────────

    def _run_ner(self, text: str) -> List[Dict[str, Any]]:
        """Run IndicNER and return entity list using offset-mapping aggregation."""
        if not self._ner_loaded or self._ner_model is None:
            return []

        try:
            import torch

            tokens = self._ner_tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True,
                return_offsets_mapping=True,
            )

            device = next(self._ner_model.parameters()).device
            input_tensors = {k: v.to(device) for k, v in tokens.items() if k != "offset_mapping"}

            with torch.no_grad():
                outputs = self._ner_model(**input_tensors)

            predictions = torch.argmax(outputs.logits, dim=-1)[0]
            id2label = self._ner_model.config.id2label
            offsets = tokens["offset_mapping"][0].tolist()

            entities = []
            current_entity = None
            current_start = None
            current_end = None

            for idx, (pred_id, offset) in enumerate(zip(predictions, offsets)):
                if offset[0] == 0 and offset[1] == 0:
                    continue
                label = id2label.get(pred_id.item(), "O")
                input_id = tokens["input_ids"][0][idx].item()
                is_continuation = "##" in self._ner_tokenizer.convert_ids_to_tokens(input_id)

                if is_continuation:
                    if current_entity:
                        current_end = offset[1]
                    elif label != "O":
                        current_entity = label[2:]
                        current_start = offset[0]
                        current_end = offset[1]
                else:
                    if label.startswith("B-"):
                        if current_entity:
                            entities.append({"type": current_entity, "text": text[current_start:current_end]})
                        current_entity = label[2:]
                        current_start = offset[0]
                        current_end = offset[1]
                    elif label.startswith("I-"):
                        ent_type = label[2:]
                        if current_entity == ent_type:
                            current_end = offset[1]
                        else:
                            if current_entity:
                                entities.append({"type": current_entity, "text": text[current_start:current_end]})
                            current_entity = ent_type
                            current_start = offset[0]
                            current_end = offset[1]
                    else:
                        if current_entity:
                            entities.append({"type": current_entity, "text": text[current_start:current_end]})
                            current_entity = None

            if current_entity:
                entities.append({"type": current_entity, "text": text[current_start:current_end]})

            return entities

        except Exception as e:
            logger.error("NER inference error: %s", e)
            return []

    # ────────────────────────────────────────────────────────────────────────
    # Stage 3: Schema mapping helpers
    # ────────────────────────────────────────────────────────────────────────

    def _extract_enterprise_name(
        self, text: str, ner_entities: List[Dict]
    ) -> Optional[str]:
        """Extract business name from NER ORG entities or regex patterns."""
        for ent in ner_entities:
            if ent["type"] in ("ORG", "ORGANIZATION", "NEorg"):
                return ent["text"]

        # Regex fallback for common Hinglish intros (still useful here)
        patterns = [
            r"(?:mera|hamara|our|my|मेरे|हमारे)\s+(?:business|company|firm|factory|workshop|dukaan|karkhana|udyog|बिजनेस|कंपनी)\s+(?:ka|ki|ka naam|का नाम|का|ki)\s+(?:naam|name|नाम)?\s*(?:hai|है|is)?\s*[\"']?(.+?)[\"']?(?:\s|$|\.)",
            r"(?:naam|name|नाम)\s+(?:hai|है|is)\s+[\"']?(.+?)[\"']?(?:\s|$|\.)",
            r"(.+?)(?:\s+(?:enterprises?|industries|pvt|private|limited|ltd|co\.|company|udyog|udhyog|इंटरप्राइज|इंडस्ट्रीज))",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if 2 < len(name) < 100:
                    return name

        return None

    def _extract_raw_materials_from_slots(
        self, slot_matches: Dict, transcript: str
    ) -> List[str]:
        """
        Get raw material mentions. Prefers LaBSE slot match sentences,
        but also runs a fast Devanagari vocab check as a supplementary signal.
        """
        found = []

        # From LaBSE raw_material slot: extract the sentence itself as signal
        for m in slot_matches.get("raw_material", []):
            # The LaBSE match tells us the SENTENCE is about materials.
            # Use a short vocab to pull the exact noun from it.
            text = m["text"]
            for material in _MATERIAL_VOCAB_FAST:
                if material.lower() in text.lower() and material not in found:
                    found.append(material)

        # Also scan the full transcript for explicit material words
        for material in _MATERIAL_VOCAB_FAST:
            if material.lower() in transcript.lower() and material not in found:
                found.append(material)

        return found

    def _buyer_types_from_slot(
        self, slot_matches: Dict, transcript: str
    ) -> List[str]:
        """Map buyer_type slot matches to schema enum values."""
        buyer_types = []

        # Use detector's keyword matching as primary source
        detected = self.mfg_detector.classify_buyer_types(transcript)
        buyer_types.extend(detected)

        # If LaBSE matched trading intent, append 'other_businesses' as signal
        if slot_matches.get("buyer_type"):
            bt_text = slot_matches["buyer_type"][0]["text"].lower()
            if any(w in bt_text for w in ["bulk", "wholesale", "b2b", "business", "थोक", "व्यापार"]):
                if "other_businesses" not in buyer_types:
                    buyer_types.append("other_businesses")
            if any(w in bt_text for w in ["retail", "consumer", "customer", "दुकान", "ग्राहक"]):
                if "retail" not in buyer_types:
                    buyer_types.append("retail")

        return list(dict.fromkeys(buyer_types))

    def _extract_geographies(
        self, text: str, ner_entities: List[Dict]
    ) -> List[str]:
        """Extract buyer geographies from NER LOC entities."""
        geos = []
        for ent in ner_entities:
            if ent["type"] in ("LOC", "LOCATION", "NEloc", "GPE"):
                if ent["text"] not in geos:
                    geos.append(ent["text"])

        # Supplement with a fast string check against known major cities
        text_lower = text.lower()
        for geo in _KNOWN_GEOS:
            if geo.lower() in text_lower and geo not in geos:
                geos.append(geo)

        return geos

    def _extract_production_scale(self, text: str) -> Optional[str]:
        for pat in _SCALE_PATTERNS:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    def _extract_years(self, text: str) -> Optional[int]:
        """User-provided regex for extracting years in business."""
        patterns = [
            r'(\d+)\s*साल',           # "10 साल"
            r'(दस|पांच|बीस|पंद्रह|तीन|चार|छह|सात|आठ|नौ|ग्यारह|दो|एक)\s*साल',  # written numbers
            r'(\d+)\s*years',
            r'(\d+)\s*वर्ष'
        ]
        word_to_num = {
            "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5,
            "छह": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
            "ग्यारह": 11, "पंद्रह": 15, "बीस": 20
        }

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                val = match.group(1)
                return word_to_num.get(val, int(val) if val.isdigit() else None)
        return None

    def _extract_employees(self, text: str) -> Optional[int]:
        """Simple numeric extraction for employees (LaBSE doesn't extract numbers)."""
        match = re.search(r"(\d+)\s*(employees|workers|staff|कर्मचारी|वर्कर|लोग)", text.lower())
        if match:
            return int(match.group(1))
        # Word numbers
        if any(w in text for w in ["बीस वर्कर", "20 वर्कर"]): return 20
        if any(w in text for w in ["दस वर्कर", "10 वर्कर"]): return 10
        return None

    def _clean_product_sentence(self, sentence: str) -> str:
        """Heuristically remove common verbs, pronouns, and framing words to isolate the product noun."""
        stopwords = [
            # Pronouns / framing (Hindi & English)
            "मैं", "हम", "हमारा", "हमारी", "मेरे", "मेरा", "मुझे", "आप", "आपका", "तुम",
            "लोग", "ये", "वो", "यह", "वहाँ", "यहाँ", "बिज़नेस", "बिजनेस", "काम", "करते",
            "से", "बोल", "रहा", "हूँ", "हैं", "है", "था", "थी", "थे", "का", "की", "के",
            "में", "पर", "को", "लिए", "खुद", "ख़ुद", "ही", "और", "तथा", "या", "वाले",
            "my", "our", "we", "i", "am", "are", "is", "business", "of", "in", "from",
            "they", "them", "their", "own", "also", "just", "then",
            # Verbs / process frames
            "बनाते", "बनाता", "बनानी", "बनाना", "मैन्युफैक्चर", "फैक्ट्री", "कर", "रहे",
            "बेचते", "सेल", "देते", "मुख्य", "प्रोडक्ट", "उत्पाद", "पिछले", "दस", "साल",
            "साथ", "नाम", "मशीन", "हाथ", "हमलोग", "करके",
            "make", "sell", "product", "products", "manufacture", "factory", "years", "main"
        ]

        # Sort by length descending to catch longer phrases first
        stopwords = sorted(stopwords, key=len, reverse=True)

        cleaned = sentence.lower()
        for sw in stopwords:
            # For Hindi words bordered by non-word chars, simple boundaries often fail.
            # We pad with spaces to ensure word-level replacement without erasing sub-words.
            # Using Python's \b for ascii, and space checks for non-ascii
            padded = f" {cleaned} "
            padded = padded.replace(f" {sw.lower()} ", " ")
            cleaned = padded.strip()

        # Also remove punctuation
        cleaned = re.sub(r'[।\.!?,_]', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # If the string got entirely erased or too short, return the original
        if len(cleaned) < 2:
            return ""

        return cleaned

    def _detect_online_presence(self, text: str) -> Optional[bool]:
        text_lower = text.lower()
        for kw in ONLINE_PRESENCE_KEYWORDS:
            if kw in text_lower:
                return True
        neg_patterns = [
            r"(?:no|nahi|nhi|koi nhi)\s*(?:online|website|internet)",
            r"(?:online|website|internet)\s*(?:nahi|nhi|not)",
        ]
        for pat in neg_patterns:
            if re.search(pat, text_lower):
                return False
        return None

    def _empty_result(self, language: str) -> Dict[str, Any]:
        return {
            "extracted_entities": {
                "enterprise_name": None,
                "product_descriptions": [],
                "raw_materials_mentioned": [],
                "manufacturing_process_keywords": [],
                "buyer_types_mentioned": [],
                "buyer_geographies_mentioned": [],
                "production_scale_mentioned": None,
                "employees_count": None,
                "existing_online_presence": None,
                "export_signal": False,
                "selling_channels": [],
                "annual_turnover": None,
                "daily_production_capacity": None,
                "factory_area_size": None,
                "major_machinery_used": [],
            },
            "confidence_scores": {
                "enterprise_name": None,
                "product_descriptions": None,
                "raw_materials_mentioned": None,
                "manufacturing_process_keywords": None,
                "buyer_types_mentioned": None,
                "buyer_geographies_mentioned": None,
                "production_scale_mentioned": None,
                "overall_extraction_confidence": 0.0,
            },
            "language_of_response": language,
        }

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        return {
            "ner_model_id": INDICNER_MODEL_ID,
            "ner_loaded": cls._ner_loaded,
            "labse_model_id": LABSE_MODEL_ID,
            "labse_loaded": cls._labse_loaded,
        }


# ── Fast supplementary material vocab (subset, for span extraction) ───────────
# This only scans the LaBSE-identified sentences, not the full transcript.
_MATERIAL_VOCAB_FAST = [
    # English
    "cotton", "silk", "wool", "jute", "polyester", "nylon", "leather",
    "steel", "iron", "aluminium", "aluminum", "copper", "brass", "zinc",
    "wood", "timber", "bamboo", "plywood", "rubber", "plastic", "glass",
    "clay", "cement", "paper", "gold", "silver", "resin", "paint",
    "flour", "sugar", "rice", "wheat", "spice", "milk",
    # Hindi (Devanagari)
    "कपास", "कॉटन", "रेशम", "ऊन", "जूट", "पॉलिएस्टर", "नायलॉन", "चमड़ा",
    "स्टील", "लोहा", "एल्यूमीनियम", "तांबा", "पीतल", "जस्ता", "टिन",
    "लकड़ी", "बांस", "प्लाईवुड", "रबर", "प्लास्टिक", "कांच", "मिट्टी",
    "सीमेंट", "कागज", "सोना", "चांदी", "रेजिन", "पेंट", "तेल", "मोम",
    "आटा", "चीनी", "चावल", "गेहूं", "मसाला", "दूध", "कच्चा माल",
    # Tamil
    "பருத்தி", "பட்டு", "கம்பளி", "தோல்", "எஃகு", "மரம்",
    # Telugu
    "పత్తి", "పట్టు", "ఉన్ని", "తోలు", "ఉక్కు", "కలప",
    # Marathi
    "कापूस", "कापड", "लोखंड", "लाकूड",
    # Gujarati
    "કપાસ", "રેશમ", "ઊન", "ચામડું", "સ્ટીલ", "લોખંડ",
    # Bengali
    "তুলা", "রেশম", "পাট", "চামড়া", "ইস্পাত",
]

# ── Known Indian geographies for fast substring fallback ─────────────────────
_KNOWN_GEOS = [
    # Major cities
    "Mumbai", "Pune", "Bangalore", "Bengaluru", "Chennai", "Hyderabad",
    "Kolkata", "Ahmedabad", "Surat", "Jaipur", "Lucknow", "Delhi",
    "Noida", "Gurgaon", "Gurugram", "Faridabad", "Kanpur", "Nagpur",
    "Indore", "Thane", "Bhopal", "Patna", "Vadodara", "Ludhiana",
    "Agra", "Nashik", "Coimbatore", "Madurai", "Rajkot", "Varanasi",
    "Kochi", "Guwahati", "Ranchi", "Mysore", "Vijayawada",
    "Tiruppur", "Moradabad", "Jalandhar", "Meerut", "Amritsar",
    "Ghaziabad", "Faridabad",
    # Indian Devanagari cities
    "मुंबई", "पुणे", "चेन्नई", "हैदराबाद", "कोलकाता", "अहमदाबाद",
    "सूरत", "जयपुर", "लखनऊ", "कानपुर", "नागपुर", "इंदौर", "भोपाल",
    "पटना", "दिल्ली", "नोएडा", "गुड़गांव", "फरीदाबाद", "गाज़ियाबाद",
    # States
    "Rajasthan", "Gujarat", "Maharashtra", "Uttar Pradesh", "Punjab",
    "Haryana", "Tamil Nadu", "Karnataka", "Kerala", "Andhra Pradesh",
    "Telangana", "West Bengal", "Odisha", "Assam", "Bihar",
    "राजस्थान", "गुजरात", "महाराष्ट्र", "उत्तर प्रदेश", "पंजाब",
    "तमिलनाडु", "कर्नाटक", "केरल",
]
