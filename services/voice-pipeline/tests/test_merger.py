"""
Tests for the Fingerprint Merger — merge logic, weighted confidence,
union geographies, completeness scoring, and merge refusal.
"""

import pytest
import uuid
from datetime import datetime, timezone

from fingerprint_merger import FingerprintMerger


def _make_voice_output(**overrides):
    """Build a minimal valid voice output dict."""
    base = {
        "module": "voice_stt_tts",
        "schema_version": "1.0.0",
        "session_id": str(uuid.uuid4()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "processing_time_ms": 1500,
        "audio_metadata": {
            "duration_seconds": 45.0,
            "language_detected": "hi",
            "language_confidence": 0.92,
            "audio_quality_score": 0.85,
            "chunks_processed": 2,
            "rounds_of_conversation": 1,
        },
        "transcript": {
            "raw_transcript": "हम स्टील का फर्नीचर बनाते हैं",
            "cleaned_transcript": "हम स्टील का फर्नीचर बनाते हैं",
            "language": "hi",
            "romanised_transcript": "",
        },
        "extracted_entities": {
            "enterprise_name": "Sharma Steel Works",
            "product_descriptions": ["steel furniture", "steel almirah"],
            "raw_materials_mentioned": ["steel", "iron"],
            "manufacturing_process_keywords": ["welding", "cutting", "polishing"],
            "buyer_types_mentioned": ["wholesale", "other_businesses"],
            "buyer_geographies_mentioned": ["Delhi", "Mumbai", "Rajasthan"],
            "production_scale_mentioned": "500 pieces per month",
            "years_in_business": 12,
            "employees_count": 25,
            "existing_online_presence": True,
        },
        "confidence_scores": {
            "enterprise_name": 0.85,
            "product_descriptions": 0.9,
            "raw_materials_mentioned": 0.8,
            "manufacturing_process_keywords": 0.6,
            "buyer_types_mentioned": 0.75,
            "buyer_geographies_mentioned": 0.7,
            "production_scale_mentioned": 0.65,
            "overall_extraction_confidence": 0.75,
        },
        "nsic_gate3_signals": {
            "manufacturing_evidence_found": True,
            "trading_evidence_found": False,
            "process_keywords_count": 3,
            "raw_material_signals_count": 2,
            "voice_mfg_confidence_score": 0.8,
            "flag_for_human_review": False,
            "flag_reason": None,
        },
        "ondc_hints": {
            "likely_sector": "Manufacturing",
            "likely_ondc_domain": "ONDC:RET1A",
            "b2b_signal": True,
            "b2c_signal": False,
            "export_signal": False,
        },
        "merge_ready": True,
        "missing_critical_fields": [],
        "conversation_complete": True,
        "partial_data_flag": False,
    }
    base.update(overrides)
    return base


def _make_ocr_output(**overrides):
    """Build a minimal valid OCR output dict."""
    base = {
        "module": "ocr_document_extraction",
        "schema_version": "1.0.0",
        "udyam": {
            "udyam_id": "UDYAM-MP-01-0012345",
            "nic_codes": ["25991", "25999"],
            "enterprise_class": "Micro",
            "major_activity": "Manufacturing",
            "district": "Indore",
            "state": "Madhya Pradesh",
        },
        "gstr1": {
            "gstin": "23AABCS1234D1ZA",
            "hsn_codes_transacted": ["9403", "7308"],
            "b2b_ratio": 0.65,
            "b2c_ratio": 0.35,
            "avg_invoice_value_inr": 45000,
            "peak_months": ["October", "November", "March"],
            "buyer_gstins_states": ["Maharashtra", "Gujarat", "Uttar Pradesh"],
            "annual_turnover_inr": 4500000,
            "manufacturing_confidence_score": 0.75,
        },
        "merge_ready": True,
    }
    base.update(overrides)
    return base


class TestFingerprintMerger:
    """Tests for fingerprint_merger.py"""

    def setup_method(self):
        self.merger = FingerprintMerger()

    def test_successful_merge(self):
        """Basic merge of valid voice + OCR should succeed."""
        voice = _make_voice_output()
        ocr = _make_ocr_output()

        fingerprint = self.merger.merge(voice, ocr)

        assert fingerprint["schema_version"] == "1.0.0"
        assert "fingerprint_id" in fingerprint
        assert "generated_at" in fingerprint
        assert "voice" in fingerprint["data_sources"]

    def test_identity_merge(self):
        """Identity section should merge voice enterprise_name + OCR ids."""
        voice = _make_voice_output()
        ocr = _make_ocr_output()

        fp = self.merger.merge(voice, ocr)

        assert fp["identity"]["enterprise_name"] == "Sharma Steel Works"
        assert fp["identity"]["udyam_id"] == "UDYAM-MP-01-0012345"
        assert fp["identity"]["gstin"] == "23AABCS1234D1ZA"
        assert fp["identity"]["enterprise_class"] == "Micro"
        assert fp["identity"]["state"] == "Madhya Pradesh"

    def test_capability_merge(self):
        """Capability should include both voice and OCR fields."""
        voice = _make_voice_output()
        ocr = _make_ocr_output()

        fp = self.merger.merge(voice, ocr)

        assert fp["capability"]["nic_codes"] == ["25991", "25999"]
        assert fp["capability"]["hsn_codes_transacted"] == ["9403", "7308"]
        assert "steel furniture" in fp["capability"]["product_descriptions_raw"]
        assert "welding" in fp["capability"]["manufacturing_process_keywords"]

    def test_buyer_geographies_union(self):
        """Buyer geographies should be union of voice + OCR."""
        voice = _make_voice_output()
        ocr = _make_ocr_output()

        fp = self.merger.merge(voice, ocr)
        geos = fp["commercial_profile"]["buyer_geographies"]

        # Voice has: Delhi, Mumbai, Rajasthan
        # OCR has: Maharashtra, Gujarat, Uttar Pradesh
        assert "Delhi" in geos
        assert "Mumbai" in geos
        assert "Maharashtra" in geos
        assert "Gujarat" in geos

    def test_manufacturing_confidence_max(self):
        """Manufacturing confidence should be MAX of voice and OCR."""
        voice = _make_voice_output()
        ocr = _make_ocr_output()
        # Voice: 0.8, OCR: 0.75 → MAX = 0.8
        fp = self.merger.merge(voice, ocr)
        assert fp["nsic_preclearance"]["manufacturing_confidence_score"] == 0.8

    def test_manufacturing_confidence_ocr_higher(self):
        """When OCR has higher manufacturing confidence, it should win."""
        voice = _make_voice_output()
        voice["nsic_gate3_signals"]["voice_mfg_confidence_score"] = 0.5
        ocr = _make_ocr_output()
        ocr["gstr1"]["manufacturing_confidence_score"] = 0.9

        fp = self.merger.merge(voice, ocr)
        assert fp["nsic_preclearance"]["manufacturing_confidence_score"] == 0.9

    def test_completeness_high(self):
        """Both sources with >80% fields → HIGH completeness."""
        voice = _make_voice_output()
        ocr = _make_ocr_output()

        fp = self.merger.merge(voice, ocr)
        assert fp["overall_data_completeness"] == "HIGH"

    def test_completeness_low(self):
        """Sparse data with single source → LOW completeness."""
        voice = _make_voice_output(
            extracted_entities={
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
            }
        )
        ocr = _make_ocr_output(
            udyam={
                "udyam_id": None,
                "nic_codes": [],
                "enterprise_class": None,
                "major_activity": None,
                "district": None,
                "state": None,
            },
            gstr1={
                "gstin": None,
                "hsn_codes_transacted": [],
                "b2b_ratio": None,
                "b2c_ratio": None,
                "avg_invoice_value_inr": None,
                "peak_months": [],
                "buyer_gstins_states": [],
                "annual_turnover_inr": None,
                "manufacturing_confidence_score": None,
            },
        )

        fp = self.merger.merge(voice, ocr)
        assert fp["overall_data_completeness"] == "LOW"

    def test_merge_refuses_not_ready_voice(self):
        """Should raise ValueError if voice merge_ready is False."""
        voice = _make_voice_output(merge_ready=False)
        ocr = _make_ocr_output()

        with pytest.raises(ValueError, match="not merge_ready"):
            self.merger.merge(voice, ocr)

    def test_merge_refuses_not_ready_ocr(self):
        """Should raise ValueError if OCR merge_ready is False."""
        voice = _make_voice_output()
        ocr = _make_ocr_output(merge_ready=False)

        with pytest.raises(ValueError, match="not merge_ready"):
            self.merger.merge(voice, ocr)

    def test_data_sources_list(self):
        """Data sources should include voice + whichever OCR sections have data."""
        voice = _make_voice_output()
        ocr = _make_ocr_output()

        fp = self.merger.merge(voice, ocr)
        assert "voice" in fp["data_sources"]
        assert "udyam" in fp["data_sources"]
        assert "gstr1" in fp["data_sources"]

    def test_voice_only_fields_preserved(self):
        """Voice-only fields should be taken as-is."""
        voice = _make_voice_output()
        ocr = _make_ocr_output()

        fp = self.merger.merge(voice, ocr)
        assert fp["scale"]["employees_count"] == 25
        assert fp["scale"]["years_in_business"] == 12
        assert fp["scale"]["production_scale_mentioned"] == "500 pieces per month"

    def test_ocr_only_fields_preserved(self):
        """OCR-only fields should be taken as-is."""
        voice = _make_voice_output()
        ocr = _make_ocr_output()

        fp = self.merger.merge(voice, ocr)
        assert fp["commercial_profile"]["annual_turnover_inr"] == 4500000
        assert fp["commercial_profile"]["avg_invoice_value_inr"] == 45000

    def test_nsic_flags(self):
        """NSIC pre-clearance flags should be populated."""
        voice = _make_voice_output()
        ocr = _make_ocr_output()

        fp = self.merger.merge(voice, ocr)
        assert isinstance(fp["nsic_preclearance"]["flags"], list)

    def test_enterprise_class_eligibility(self):
        """Micro class should be eligible."""
        voice = _make_voice_output()
        ocr = _make_ocr_output()

        fp = self.merger.merge(voice, ocr)
        assert fp["nsic_preclearance"]["enterprise_class_eligible"] is True

    def test_ondc_mapping(self):
        """ONDC mapping should be derived from signals."""
        voice = _make_voice_output()
        ocr = _make_ocr_output()

        fp = self.merger.merge(voice, ocr)
        assert "likely_ondc_domain" in fp["ondc_mapping"]
        assert isinstance(fp["ondc_mapping"]["b2b_signal"], bool)
        assert isinstance(fp["ondc_mapping"]["b2c_signal"], bool)

    def test_validate_voice_input(self):
        """Voice input validation should pass for valid input."""
        voice = _make_voice_output()
        result = self.merger.validate_voice_input(voice)
        assert result["valid"] is True

    def test_validate_voice_input_wrong_module(self):
        """Voice input with wrong module should fail."""
        voice = _make_voice_output(module="wrong_module")
        result = self.merger.validate_voice_input(voice)
        assert result["valid"] is False

    def test_validate_voice_input_missing_keys(self):
        """Voice input missing required keys should fail."""
        result = self.merger.validate_voice_input({"some": "data"})
        assert result["valid"] is False
