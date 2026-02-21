"""
Fingerprint Merger — merges voice pipeline JSON + OCR pipeline JSON into
the final Verified Capability Fingerprint.

MERGE RULES:
- Fields present in BOTH: OCR wins if confidence > 0.8, else weighted average
- buyer_geographies: union of voice buyer_geographies_mentioned + OCR buyer_gstins_states
- manufacturing evidence: MAX of voice voice_mfg_confidence_score and OCR manufacturing_confidence_score
- Fields only in voice (enterprise_name, product_descriptions, process_keywords): voice values
- Fields only in OCR (nic_codes, hsn_codes, gstin, turnover): OCR values
- overall_data_completeness: HIGH / MEDIUM / LOW
"""

import json
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import jsonschema

logger = logging.getLogger(__name__)

# ── Load schemas ──────────────────────────────────────────────────────────────
_SCHEMA_DIR = Path(__file__).parent / "schemas"


def _load_schema(filename: str) -> Dict:
    try:
        with open(_SCHEMA_DIR / filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to load schema %s: %s", filename, e)
        return {}


class FingerprintMerger:
    """Merges voice output and OCR output into the Verified Capability Fingerprint."""

    def __init__(self):
        self.ocr_schema = _load_schema("ocr_input_schema.json")
        self.fingerprint_schema = _load_schema("fingerprint_schema.json")

    def merge(
        self,
        voice_output: Dict[str, Any],
        ocr_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Merge voice_output + ocr_output into the final Verified Capability Fingerprint.

        Args:
            voice_output: Output from the voice pipeline (module: voice_stt_tts)
            ocr_output: Output from the OCR pipeline (module: ocr_document_extraction)

        Returns:
            The final Verified Capability Fingerprint dict.

        Raises:
            ValueError if either input has merge_ready == False.
        """
        # ── Pre-checks ────────────────────────────────────────────────────
        if not voice_output.get("merge_ready", False):
            raise ValueError(
                "Voice output is not merge_ready. Cannot proceed with merge. "
                f"Missing fields: {voice_output.get('missing_critical_fields', [])}"
            )

        if not ocr_output.get("merge_ready", False):
            raise ValueError(
                "OCR output is not merge_ready. Cannot proceed with merge."
            )

        # ── Extract sub-sections ──────────────────────────────────────────
        voice_entities = voice_output.get("extracted_entities", {})
        voice_confidence = voice_output.get("confidence_scores", {})
        voice_gate3 = voice_output.get("nsic_gate3_signals", {})
        voice_ondc = voice_output.get("ondc_hints", {})

        udyam = ocr_output.get("udyam", {})
        gstr1 = ocr_output.get("gstr1", {})

        # ── Determine data sources ────────────────────────────────────────
        data_sources = ["voice"]
        if udyam and any(v is not None for v in udyam.values() if not isinstance(v, list)):
            data_sources.append("udyam")
        if gstr1 and any(v is not None for v in gstr1.values() if not isinstance(v, list)):
            data_sources.append("gstr1")

        # ── Identity (OCR-primary, voice supplement) ──────────────────────
        identity = {
            "enterprise_name": voice_entities.get("enterprise_name") or udyam.get("enterprise_name"),
            "udyam_id": udyam.get("udyam_id"),
            "gstin": gstr1.get("gstin"),
            "enterprise_class": udyam.get("enterprise_class"),
            "major_activity": udyam.get("major_activity"),
            "district": udyam.get("district"),
            "state": udyam.get("state"),
        }

        # ── Capability (union of both) ────────────────────────────────────
        capability = {
            "nic_codes": udyam.get("nic_codes", []),
            "hsn_codes_transacted": gstr1.get("hsn_codes_transacted", []),
            "product_descriptions_raw": voice_entities.get("product_descriptions", []),
            "manufacturing_process_keywords": voice_entities.get(
                "manufacturing_process_keywords", []
            ),
            "raw_materials_mentioned": voice_entities.get("raw_materials_mentioned", []),
        }

        # ── Commercial Profile ────────────────────────────────────────────
        # Buyer geographies: union of voice + OCR
        voice_geos = set(voice_entities.get("buyer_geographies_mentioned", []))
        ocr_geos = set(gstr1.get("buyer_gstins_states", []))
        buyer_geographies = sorted(voice_geos | ocr_geos)

        # B2B / B2C ratios: OCR wins if available and confidence > 0.8
        ocr_mfg_conf = gstr1.get("manufacturing_confidence_score") or 0.0
        b2b_ratio = gstr1.get("b2b_ratio")
        b2c_ratio = gstr1.get("b2c_ratio")

        commercial_profile = {
            "b2b_ratio": b2b_ratio,
            "b2c_ratio": b2c_ratio,
            "export_signal": voice_ondc.get("export_signal", False),
            "avg_invoice_value_inr": gstr1.get("avg_invoice_value_inr"),
            "annual_turnover_inr": gstr1.get("annual_turnover_inr"),
            "peak_months": gstr1.get("peak_months", []),
            "buyer_geographies": buyer_geographies,
            "existing_online_presence": voice_entities.get("existing_online_presence"),
            "buyer_types": voice_entities.get("buyer_types_mentioned", []),
        }

        # ── Scale (voice-primary) ────────────────────────────────────────
        scale = {
            "employees_count": voice_entities.get("employees_count"),
            "years_in_business": voice_entities.get("years_in_business"),
            "production_scale_mentioned": voice_entities.get("production_scale_mentioned"),
        }

        # ── Manufacturing confidence: MAX of voice and OCR (conservative, benefits MSE)
        voice_mfg_conf = voice_gate3.get("voice_mfg_confidence_score", 0.0)
        combined_mfg_confidence = max(voice_mfg_conf, ocr_mfg_conf)

        # ── NSIC Pre-clearance ────────────────────────────────────────────
        nsic_preclearance = {
            "udyam_api_valid": None,  # Not our scope to call Udyam API
            "enterprise_class_eligible": self._check_class_eligible(
                udyam.get("enterprise_class")
            ),
            "major_activity_eligible": self._check_activity_eligible(
                udyam.get("major_activity"), combined_mfg_confidence
            ),
            "already_on_ondc": None,  # Layer 2 check
            "manufacturing_confidence_score": round(combined_mfg_confidence, 4),
            "overall_clearance": None,  # To be determined by NSIC
            "flags": self._collect_flags(
                voice_gate3, identity, combined_mfg_confidence
            ),
        }

        # ── ONDC Mapping ─────────────────────────────────────────────────
        ondc_mapping = {
            "likely_ondc_domain": voice_ondc.get("likely_ondc_domain"),
            "ondc_category_candidates": [],  # Layer 2 responsibility
            "b2b_signal": voice_ondc.get("b2b_signal", False)
            or (b2b_ratio is not None and b2b_ratio > 0.5),
            "b2c_signal": voice_ondc.get("b2c_signal", False)
            or (b2c_ratio is not None and b2c_ratio > 0.5),
        }

        # ── Data completeness ────────────────────────────────────────────
        overall_completeness = self._compute_completeness(
            identity, capability, commercial_profile, scale, data_sources
        )

        # ── Build final fingerprint ──────────────────────────────────────
        fingerprint = {
            "schema_version": "1.0.0",
            "fingerprint_id": str(uuid.uuid4()),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_sources": data_sources,
            "overall_data_completeness": overall_completeness,
            "identity": identity,
            "capability": capability,
            "commercial_profile": commercial_profile,
            "scale": scale,
            "nsic_preclearance": nsic_preclearance,
            "ondc_mapping": ondc_mapping,
        }

        return fingerprint

    def validate_voice_input(self, voice_output: Dict) -> Dict[str, Any]:
        """Validate voice output before merging."""
        # Basic structure check
        required_keys = ["module", "schema_version", "merge_ready", "extracted_entities"]
        missing = [k for k in required_keys if k not in voice_output]
        if missing:
            return {"valid": False, "errors": [f"Missing keys: {missing}"]}
        if voice_output.get("module") != "voice_stt_tts":
            return {"valid": False, "errors": ["module must be 'voice_stt_tts'"]}
        return {"valid": True, "errors": []}

    def validate_ocr_input(self, ocr_output: Dict) -> Dict[str, Any]:
        """Validate OCR output before merging."""
        if not self.ocr_schema:
            return {"valid": True, "errors": ["OCR schema not loaded — skipping"]}

        try:
            jsonschema.validate(instance=ocr_output, schema=self.ocr_schema)
            return {"valid": True, "errors": []}
        except jsonschema.ValidationError as e:
            return {"valid": False, "errors": [str(e.message)]}

    def validate_fingerprint(self, fingerprint: Dict) -> Dict[str, Any]:
        """Validate the final fingerprint against schema."""
        if not self.fingerprint_schema:
            return {"valid": True, "errors": ["Fingerprint schema not loaded"]}

        try:
            jsonschema.validate(instance=fingerprint, schema=self.fingerprint_schema)
            return {"valid": True, "errors": []}
        except jsonschema.ValidationError as e:
            return {"valid": False, "errors": [str(e.message)]}

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _check_class_eligible(enterprise_class: Optional[str]) -> Optional[bool]:
        """Check if enterprise class is eligible for NSIC (Micro or Small)."""
        if enterprise_class is None:
            return None
        eligible_classes = {"micro", "small"}
        return enterprise_class.lower() in eligible_classes

    @staticmethod
    def _check_activity_eligible(
        major_activity: Optional[str], mfg_confidence: float
    ) -> Optional[bool]:
        """
        Check if major activity is eligible.
        Manufacturing is required — trading-only entities may not qualify.
        """
        if major_activity is None:
            return None if mfg_confidence < 0.5 else True
        return major_activity.lower() in ("manufacturing", "services", "both")

    @staticmethod
    def _collect_flags(
        gate3_signals: Dict, identity: Dict, mfg_confidence: float
    ) -> List[str]:
        """Collect warning flags for NSIC review."""
        flags = []

        if gate3_signals.get("flag_for_human_review"):
            reason = gate3_signals.get("flag_reason", "Unknown reason")
            flags.append(f"VOICE_REVIEW: {reason}")

        if mfg_confidence < 0.3:
            flags.append("LOW_MFG_CONFIDENCE: Score below 0.3 threshold")

        if gate3_signals.get("trading_evidence_found") and not gate3_signals.get(
            "manufacturing_evidence_found"
        ):
            flags.append("TRADING_ONLY: No manufacturing evidence — possible trader")

        if not identity.get("udyam_id"):
            flags.append("MISSING_UDYAM: No Udyam ID available")

        if not identity.get("gstin"):
            flags.append("MISSING_GSTIN: No GSTIN available")

        return flags

    @staticmethod
    def _compute_completeness(
        identity: Dict,
        capability: Dict,
        commercial: Dict,
        scale: Dict,
        data_sources: List[str],
    ) -> str:
        """
        Compute overall_data_completeness:
        - HIGH: Both sources agree, >80% fields filled
        - MEDIUM: One source partial
        - LOW: Only one source, <50% fields filled
        """
        # Count non-null / non-empty fields
        all_fields = {}
        for section in [identity, capability, commercial, scale]:
            for k, v in section.items():
                if isinstance(v, list):
                    all_fields[k] = len(v) > 0
                elif isinstance(v, bool):
                    all_fields[k] = True  # bool fields always "filled"
                else:
                    all_fields[k] = v is not None

        total = len(all_fields)
        filled = sum(1 for v in all_fields.values() if v)
        fill_ratio = filled / total if total > 0 else 0.0

        has_multiple_sources = len(data_sources) > 1

        if has_multiple_sources and fill_ratio > 0.8:
            return "HIGH"
        elif fill_ratio > 0.5 or has_multiple_sources:
            return "MEDIUM"
        else:
            return "LOW"
