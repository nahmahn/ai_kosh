"""
Manufacturing Detector — Gate 3 probability scorer using MuRIL zero-shot classification.

Architecture (per user design):
  - google/muril-base-cased for zero-shot classification (mfg vs trading)
  - LaBSE slot confidences from EntityExtractor to provide supplementary signals
  - Composite probability score replaces the old boolean keyword-count logic

Scoring formula:
  score = 0.40 * muril_mfg_prob
        + 0.25 * raw_material_confidence
        + 0.25 * manufacturing_process_confidence
        + 0.10 * (1 - muril_trading_prob)

  If strong trading signal but no process signal → apply 0.5x penalty.
  Final score clamped to [0.0, 1.0].

Gate 3 logic:
  score > 0.60  → manufacturing_evidence_found = True
  0.40 < score ≤ 0.60  → flag_for_human_review = True
  score ≤ 0.40  → likely not a manufacturer → ask follow-up
"""

import logging
import threading
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# ── Zero-shot classification model config ───────────────────────────────────
# We use mDeBERTa-v3-base-mnli-xnli instead of MuRIL base because zero-shot
# classification via HuggingFace requires an NLI (Natural Language Inference)
# trained model. MuRIL base is only pre-trained with MLM.
MURIL_MODEL_ID = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"

# Zero-shot classification labels (NLI hypotheses)
MFG_LABELS = [
    "we manufacture goods ourselves in our factory",
    "we buy finished goods and resell them without making anything",
    "we provide services",
    "we both make and sell our own products",
]

# ── Buyer type keywords (kept as fast lookup — language independent enough) ──
_BUYER_TYPE_KEYWORDS = {
    "wholesale": [
        "wholesale", "थोक", "bulk", "थोकिया", "bulk order",
        "ਥੋਕ", "जमलेवाल", "ঘাউস",
    ],
    "retail": [
        "retail", "फुटकर", "dukaan", "दुकान", "shop", "shops",
    ],
    "government": [
        "government", "govt", "sarkari", "सरकारी", "tender", "PSU",
    ],
    "export": [
        "export", "exports", "विदेश", "foreign", "international",
        "abroad", "overseas",
    ],
    "direct_consumer": [
        "direct", "consumer", "end user", "customer", "ग्राहक", "retail", "b2c",
    ],
    "other_businesses": [
        "other businesses", "b2b", "manufacturer", "company", "factory",
        "distributors", "agents", "dealer", "reseller",
    ],
}


class ManufacturingDetector:
    """
    Computes Gate 3 manufacturing vs trading probability score
    using MuRIL zero-shot classification + LaBSE slot confidences.
    """

    _muril_classifier = None
    _muril_loaded = False
    _muril_error: Optional[str] = None
    _muril_lock = threading.Lock()

    def __init__(self):
        pass  # Lazy loading — model loads on first use

    @classmethod
    def load_muril_model(cls) -> bool:
        """Load MuRIL zero-shot classifier. Call at startup."""
        if cls._muril_loaded:
            return True

        with cls._muril_lock:
            if cls._muril_loaded:
                return True
            try:
                import torch
                from transformers import pipeline

                device = 0 if torch.cuda.is_available() else -1
                logger.info("Loading MuRIL zero-shot classifier: %s", MURIL_MODEL_ID)
                cls._muril_classifier = pipeline(
                    "zero-shot-classification",
                    model=MURIL_MODEL_ID,
                    device=device,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else None,
                )
                cls._muril_loaded = True
                logger.info("MuRIL loaded on device %s", device)
                return True
            except Exception as e:
                cls._muril_error = str(e)
                logger.error("Failed to load MuRIL: %s", e)
                return False

    def compute_gate3_score(
        self,
        transcript: str,
        slot_matches: Optional[Dict[str, List[Dict]]] = None,
        extracted_entities: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Compute the Gate 3 composite manufacturing confidence score.

        Args:
            transcript: The cleaned transcript text.
            slot_matches: (Legacy) LaBSE slot fill output.
            extracted_entities: JSON payload returned by the LLM.

        Returns:
            Dict matching nsic_gate3_signals schema.
        """
        # ── LLM Optimization Path ────────────────────────────────────────────
        if extracted_entities:
            mfg_keywords = extracted_entities.get("manufacturing_process_keywords", [])
            rm_keywords = extracted_entities.get("raw_materials_mentioned", [])
            
            manufacturing_found = len(mfg_keywords) > 0
            score = 0.9 if manufacturing_found else 0.1
            
            flag_for_review = len(mfg_keywords) == 0 and len(rm_keywords) > 0
            if flag_for_review: 
                score = 0.5
            
            return {
                "manufacturing_evidence_found": manufacturing_found,
                "trading_evidence_found": not manufacturing_found,
                "process_keywords_count": len(mfg_keywords),
                "raw_material_signals_count": len(rm_keywords),
                "voice_mfg_confidence_score": round(score, 3),
                "flag_for_human_review": flag_for_review,
                "flag_reason": "Mentioned raw materials but no explicit manufacturing process." if flag_for_review else ("Insufficient evidence of own manufacturing" if not manufacturing_found else None),
            }

        # ── Signal 1: MuRIL zero-shot classification (Legacy fallback) ───────
        muril_mfg_prob = 0.0
        muril_trading_prob = 0.0
        process_kw_count = 0

        if self._muril_loaded and self._muril_classifier and transcript.strip():
            try:
                result = self._muril_classifier(
                    transcript[:512],  # MuRIL max 512 tokens
                    candidate_labels=MFG_LABELS,
                    multi_label=False,
                )
                label_scores = dict(zip(result["labels"], result["scores"]))
                muril_mfg_prob = label_scores.get("we manufacture goods ourselves in our factory", 0.0)
                trading_prob_raw = label_scores.get("we buy finished goods and resell them without making anything", 0.0)
                mixed_prob = label_scores.get("we both make and sell our own products", 0.0)
                muril_trading_prob = trading_prob_raw
                # Mixed counts somewhat as manufacturing
                muril_mfg_prob = muril_mfg_prob + 0.5 * mixed_prob
            except Exception as e:
                logger.error("MuRIL inference error: %s", e)

        # ── Signal 2: LaBSE slot confidences ─────────────────────────────────
        rm_matches = slot_matches.get("raw_material", [])
        proc_matches = slot_matches.get("manufacturing_process", [])
        trading_matches = slot_matches.get("trading", [])

        rm_confidence = max((m["confidence"] for m in rm_matches), default=0.0)
        proc_confidence = max((m["confidence"] for m in proc_matches), default=0.0)
        trading_signal_conf = max((m["confidence"] for m in trading_matches), default=0.0)

        has_raw_material = rm_confidence > 0.45
        has_process = proc_confidence > 0.45
        has_trading_signal = trading_signal_conf > 0.50

        process_kw_count = len(proc_matches)

        # ── Composite score ───────────────────────────────────────────────────
        score = (
            0.40 * muril_mfg_prob
            + 0.25 * rm_confidence
            + 0.25 * proc_confidence
            + 0.10 * (1.0 - muril_trading_prob)
        )

        # Penalty: trading evidence without any manufacturing process confirmation
        if has_trading_signal and not has_process and not has_raw_material:
            score *= 0.5

        score = max(0.0, min(1.0, score))

        # ── Gate 3 decision ───────────────────────────────────────────────────
        manufacturing_found = score > 0.60
        flag_for_review = 0.40 < score <= 0.60
        flag_reason = None
        if flag_for_review:
            flag_reason = "Borderline manufacturing signal — needs one more confirming utterance"
        elif not manufacturing_found:
            flag_reason = "Insufficient evidence of own manufacturing"

        return {
            "manufacturing_evidence_found": manufacturing_found,
            "trading_evidence_found": has_trading_signal,
            "process_keywords_count": process_kw_count,
            "raw_material_signals_count": len(rm_matches),
            "voice_mfg_confidence_score": round(score, 3),
            "flag_for_human_review": flag_for_review,
            "flag_reason": flag_reason,
        }

    def detect_manufacturing_keywords(
        self, transcript: str, language: str = "hi"
    ) -> List[str]:
        """
        Detects manufacturing process keywords and returns the actual words found in the transcript.
        """
        found = []
        lower = transcript.lower()
        
        # We search for these keywords and if found, append the actual keyword
        # to the list so the JSON output contains literal words instead of abstract slugs.
        keywords = [
            "बनाते", "बनाना", "फैक्ट्री", "कारखाना", "factory", "manufacture",
            "banate", "karkhana", "production", "workshop",
            "நூற்பு", "தொழிற்சாலை",  # Tamil: spinning, factory
            "తయారు", "ఫ్యాక్టరీ",     # Telugu: make, factory
            "बनवतो", "कारखाना",      # Marathi
            "બનાવીએ", "ફેક્ટ્રી",    # Gujarati
            "তৈরি", "কারখানা",       # Bengali
        ]
        
        for kw in keywords:
            if kw in lower:
                found.append(kw)

        return found

    def classify_buyer_types(self, transcript: str) -> List[str]:
        """Keyword-based buyer type classification (fast, language-aware)."""
        transcript_lower = transcript.lower()
        detected = []
        for buyer_type, keywords in _BUYER_TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in transcript_lower:
                    if buyer_type not in detected:
                        detected.append(buyer_type)
                    break
        return detected

    # ── Legacy method shim (some callers used build_gate3_signals) ────────────
    def build_gate3_signals(
        self,
        transcript: str,
        extracted_entities: Dict,
        slot_matches: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Bridge method for backward compatibility.
        Calls compute_gate3_score and returns the same schema.
        """
        return self.compute_gate3_score(
            transcript=transcript,
            slot_matches=slot_matches or {},
        )

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        return {
            "muril_model_id": MURIL_MODEL_ID,
            "muril_loaded": cls._muril_loaded,
            "muril_error": cls._muril_error,
        }
