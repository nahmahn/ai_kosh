"""
Layer 1 Integration Test - tests the OCR + Voice merge pipeline end-to-end.

No GPU, no API keys, no running services needed.
This tests the FingerprintMerger directly with realistic mock data.

Run with:
    cd voice_pipeline
    python -m pytest ../test_integration.py -v --tb=short

Or standalone:
    python test_integration.py
"""

import sys
import os
import json

# Add voice_pipeline to path so we can import the merger
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "voice_pipeline"))

from fingerprint_merger import FingerprintMerger


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK DATA — realistic outputs from each pipeline
# ═══════════════════════════════════════════════════════════════════════════════

MOCK_OCR_UDYAM_ONLY = {
    "module": "ocr_document_extraction",
    "schema_version": "1.0.0",
    "merge_ready": True,
    "udyam": {
        "udyam_id": "UDYAM-UK-05-0032800",
        "enterprise_name": "AVINYA AUTOMOTIVE PRIVATE LIMITED",
        "nic_2digit": "45",
        "nic_5digit": "45200",
        "enterprise_class": "Micro",
        "major_activity": "Manufacturing",
        "district": "Dehradun",
        "state": "Uttarakhand",
        "gstin_from_udyam": "05AABCA1234B1Z5",
        "date_of_incorporation": "01/04/2019",
        "social_category": "General",
        "extraction_confidence": 0.83,
    },
    "gstr1": None,
    "nsic_preclearance": {
        "manufacturing_confidence_score": 0.9,
        "trading_pattern_detected": False,
        "nsic_gate3_status": "AUTO_APPROVE",
        "flag_reason": None,
    },
    "documents_processed": ["udyam"],
    "partial_data_flag": False,
}

MOCK_OCR_GST_ONLY = {
    "module": "ocr_document_extraction",
    "schema_version": "1.0.0",
    "merge_ready": True,
    "udyam": None,
    "gstr1": {
        "gstin": "05AABCA1234B1Z5",
        "financial_year": "2024-25",
        "tax_period": "October 2024",
        "hsn_codes_transacted": ["5208", "5513", "5209"],
        "b2b_ratio": 0.85,
        "b2c_ratio": 0.15,
        "b2b_total_taxable_value": 900000.0,
        "b2c_total_taxable_value": 158000.0,
        "avg_invoice_value_inr": 112500.0,
        "annual_turnover_inr": 18200000.0,
        "buyer_gstins_states": ["Gujarat", "Maharashtra", "Rajasthan"],
        "manufacturing_confidence_score": 0.82,
    },
    "nsic_preclearance": {
        "manufacturing_confidence_score": 0.82,
        "trading_pattern_detected": False,
        "raw_material_hsn_found": True,
        "finished_good_hsn_found": True,
        "nsic_gate3_status": "AUTO_APPROVE",
        "flag_reason": None,
    },
    "documents_processed": ["gstr1"],
    "partial_data_flag": False,
}

MOCK_OCR_BOTH = {
    "module": "ocr_document_extraction",
    "schema_version": "1.0.0",
    "merge_ready": True,
    "udyam": MOCK_OCR_UDYAM_ONLY["udyam"],
    "gstr1": MOCK_OCR_GST_ONLY["gstr1"],
    "nsic_preclearance": MOCK_OCR_GST_ONLY["nsic_preclearance"],
    "documents_processed": ["udyam", "gstr1"],
    "partial_data_flag": False,
}

MOCK_VOICE_OUTPUT = {
    "module": "voice_stt_tts",
    "schema_version": "1.0.0",
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "timestamp_utc": "2026-03-01T18:00:00Z",
    "processing_time_ms": 4200,
    "audio_metadata": {
        "duration_seconds": 45.2,
        "language_detected": "hi",
        "language_confidence": 0.92,
        "audio_quality_score": 0.85,
        "chunks_processed": 3,
        "rounds_of_conversation": 5,
    },
    "transcript": {
        "raw_transcript": "हमारी कंपनी एविन्या ऑटोमोटिव है हम ऑटोमोबाइल पार्ट्स बनाते हैं",
        "cleaned_transcript": "Hamari company Avinya Automotive hai, hum automobile parts banate hain.",
        "language": "hi",
        "romanised_transcript": "hamari company avinya automotive hai hum automobile parts banate hain",
    },
    "extracted_entities": {
        "enterprise_name": "Avinya Automotive",
        "product_descriptions": [
            "automobile spare parts",
            "engine components",
            "brake assemblies",
        ],
        "raw_materials_mentioned": ["steel sheets", "aluminum rods", "rubber gaskets"],
        "manufacturing_process_keywords": [
            "CNC machining",
            "die casting",
            "heat treatment",
            "powder coating",
        ],
        "buyer_types_mentioned": ["wholesale", "other_businesses"],
        "buyer_geographies_mentioned": ["Delhi", "Haryana", "Punjab"],
        "production_scale_mentioned": "500 units per day",
        "years_in_business": 6,
        "employees_count": 35,
        "existing_online_presence": False,
        "daily_production_capacity": "500 units",
        "factory_area_size": "2000 sq ft",
        "major_machinery_used": ["CNC lathe", "hydraulic press", "welding station"],
    },
    "confidence_scores": {
        "enterprise_name": 0.95,
        "product_descriptions": 0.88,
        "raw_materials_mentioned": 0.75,
        "manufacturing_process_keywords": 0.82,
        "buyer_types_mentioned": 0.70,
        "buyer_geographies_mentioned": 0.65,
        "production_scale_mentioned": 0.78,
        "overall_extraction_confidence": 0.79,
    },
    "nsic_gate3_signals": {
        "manufacturing_evidence_found": True,
        "trading_evidence_found": False,
        "process_keywords_count": 4,
        "raw_material_signals_count": 3,
        "voice_mfg_confidence_score": 0.88,
        "flag_for_human_review": False,
        "flag_reason": None,
    },
    "ondc_hints": {
        "likely_sector": "Manufacturing",
        "likely_ondc_domain": "Manufacturing & Industrial",
        "b2b_signal": True,
        "b2c_signal": False,
        "export_signal": False,
    },
    "merge_ready": True,
    "missing_critical_fields": [],
    "conversation_complete": True,
    "partial_data_flag": False,
}


# ═══════════════════════════════════════════════════════════════════════════════
# TEST HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def separator(title: str):
    print(f"\n{'═' * 70}")
    print(f"  {title}")
    print(f"{'═' * 70}")


def check(condition: bool, label: str):
    status = "✅ PASS" if condition else "❌ FAIL"
    print(f"  {status} — {label}")
    return condition


def pretty_json(data: dict, indent: int = 2) -> str:
    return json.dumps(data, indent=indent, default=str, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1: Full merge (Udyam + GST OCR + Voice)
# ═══════════════════════════════════════════════════════════════════════════════

def test_full_merge():
    separator("TEST 1: Full Merge (Udyam + GST + Voice)")
    merger = FingerprintMerger()
    
    fingerprint = merger.merge(MOCK_VOICE_OUTPUT, MOCK_OCR_BOTH)
    
    all_passed = True
    
    # Schema validation
    validation = merger.validate_fingerprint(fingerprint)
    all_passed &= check(validation["valid"], f"Fingerprint passes schema validation (errors: {validation['errors']})")
    
    # Identity — OCR wins
    identity = fingerprint["identity"]
    all_passed &= check(identity["udyam_id"] == "UDYAM-UK-05-0032800", "Udyam ID from OCR")
    all_passed &= check(identity["gstin"] == "05AABCA1234B1Z5", "GSTIN from GST return")
    all_passed &= check(identity["enterprise_class"] == "Micro", "Enterprise class from Udyam")
    all_passed &= check(identity["major_activity"] == "Manufacturing", "Major activity from Udyam")
    all_passed &= check(identity["state"] == "Uttarakhand", "State from Udyam")
    all_passed &= check(identity["district"] == "Dehradun", "District from Udyam")
    
    # Enterprise name — voice can supplement, but OCR has it too
    all_passed &= check(identity["enterprise_name"] is not None, "Enterprise name present")
    
    # Capability — union
    cap = fingerprint["capability"]
    all_passed &= check("45200" in cap["nic_codes"] or "45" in cap["nic_codes"], 
                        f"NIC codes from Udyam: {cap['nic_codes']}")
    all_passed &= check(len(cap["hsn_codes_transacted"]) == 3, 
                        f"HSN codes from GST: {cap['hsn_codes_transacted']}")
    all_passed &= check(len(cap["product_descriptions_raw"]) == 3, 
                        f"Product descriptions from voice: {cap['product_descriptions_raw']}")
    all_passed &= check(len(cap["manufacturing_process_keywords"]) == 4, 
                        f"Mfg keywords from voice: {cap['manufacturing_process_keywords']}")
    all_passed &= check(len(cap["raw_materials_mentioned"]) == 3, 
                        f"Raw materials from voice: {cap['raw_materials_mentioned']}")
    
    # Commercial profile
    comm = fingerprint["commercial_profile"]
    all_passed &= check(comm["b2b_ratio"] == 0.85, f"B2B ratio from GST: {comm['b2b_ratio']}")
    all_passed &= check(comm["b2c_ratio"] == 0.15, f"B2C ratio from GST: {comm['b2c_ratio']}")
    all_passed &= check(comm["annual_turnover_inr"] == 18200000.0, "Annual turnover from GST")
    all_passed &= check(comm["avg_invoice_value_inr"] == 112500.0, "Avg invoice from GST")
    
    # Buyer geographies — UNION of voice + OCR
    geos = comm["buyer_geographies"]
    all_passed &= check("Gujarat" in geos, "Gujarat from OCR GST")
    all_passed &= check("Delhi" in geos, "Delhi from Voice")
    all_passed &= check("Haryana" in geos, "Haryana from Voice")
    all_passed &= check("Rajasthan" in geos, "Rajasthan from OCR GST")
    all_passed &= check(len(geos) >= 5, f"Union has >= 5 states: {geos}")
    
    # Scale — from voice
    scale = fingerprint["scale"]
    all_passed &= check(scale["employees_count"] == 35, "Employees from voice")
    all_passed &= check(scale["years_in_business"] == 6, "Years from voice")
    all_passed &= check(scale["production_scale_mentioned"] == "500 units per day", "Scale from voice")
    
    # Manufacturing confidence — MAX of voice (0.88) and OCR (0.82) = 0.88
    nsic = fingerprint["nsic_preclearance"]
    all_passed &= check(nsic["manufacturing_confidence_score"] >= 0.88, 
                        f"Mfg confidence is MAX: {nsic['manufacturing_confidence_score']}")
    all_passed &= check(nsic["enterprise_class_eligible"] == True, "Micro is NSIC eligible")
    all_passed &= check(nsic["major_activity_eligible"] == True, "Manufacturing is eligible")
    
    # Data completeness
    all_passed &= check(fingerprint["overall_data_completeness"] == "HIGH", 
                        f"Completeness: {fingerprint['overall_data_completeness']}")
    
    # Data sources
    all_passed &= check("voice" in fingerprint["data_sources"], "Voice in data sources")
    all_passed &= check("udyam" in fingerprint["data_sources"], "Udyam in data sources")
    all_passed &= check("gstr1" in fingerprint["data_sources"], "GSTR1 in data sources")
    
    if all_passed:
        print(f"\n  🎉 TEST 1 PASSED — All {30} assertions verified")
    else:
        print(f"\n  ⚠️  TEST 1 HAD FAILURES — check output above")
    
    return all_passed, fingerprint


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: Udyam-only OCR + Voice (no GST)
# ═══════════════════════════════════════════════════════════════════════════════

def test_udyam_only_merge():
    separator("TEST 2: Udyam-Only OCR + Voice (no GST)")
    merger = FingerprintMerger()
    
    fingerprint = merger.merge(MOCK_VOICE_OUTPUT, MOCK_OCR_UDYAM_ONLY)
    
    all_passed = True
    
    validation = merger.validate_fingerprint(fingerprint)
    all_passed &= check(validation["valid"], f"Schema valid (errors: {validation['errors']})")
    
    identity = fingerprint["identity"]
    all_passed &= check(identity["udyam_id"] == "UDYAM-UK-05-0032800", "Udyam ID present")
    all_passed &= check(identity["gstin"] is None, "No GSTIN (no GST return)")
    
    cap = fingerprint["capability"]
    all_passed &= check("45200" in cap["nic_codes"] or "45" in cap["nic_codes"], 
                        f"NIC from Udyam: {cap['nic_codes']}")
    all_passed &= check(len(cap["hsn_codes_transacted"]) == 0, "No HSN codes (no GST)")
    all_passed &= check(len(cap["product_descriptions_raw"]) == 3, "Products from voice")
    
    comm = fingerprint["commercial_profile"]
    all_passed &= check(comm["b2b_ratio"] is None, "No B2B ratio (no GST)")
    all_passed &= check(comm["annual_turnover_inr"] is None, "No turnover (no GST)")
    
    # Geographies only from voice
    geos = comm["buyer_geographies"]
    all_passed &= check(len(geos) == 3, f"3 states from voice only: {geos}")
    
    all_passed &= check("voice" in fingerprint["data_sources"], "Voice in sources")
    all_passed &= check("udyam" in fingerprint["data_sources"], "Udyam in sources")
    all_passed &= check("gstr1" not in fingerprint["data_sources"], "No GSTR1 in sources")
    
    if all_passed:
        print(f"\n  🎉 TEST 2 PASSED")
    else:
        print(f"\n  ⚠️  TEST 2 HAD FAILURES")
    
    return all_passed, fingerprint


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: GST-only OCR + Voice (no Udyam)
# ═══════════════════════════════════════════════════════════════════════════════

def test_gst_only_merge():
    separator("TEST 3: GST-Only OCR + Voice (no Udyam)")
    merger = FingerprintMerger()
    
    fingerprint = merger.merge(MOCK_VOICE_OUTPUT, MOCK_OCR_GST_ONLY)
    
    all_passed = True
    
    validation = merger.validate_fingerprint(fingerprint)
    all_passed &= check(validation["valid"], f"Schema valid (errors: {validation['errors']})")
    
    identity = fingerprint["identity"]
    all_passed &= check(identity["udyam_id"] is None, "No Udyam ID")
    all_passed &= check(identity["gstin"] == "05AABCA1234B1Z5", "GSTIN from GST")
    all_passed &= check(identity["enterprise_name"] is not None, "Name from voice fallback")
    
    cap = fingerprint["capability"]
    all_passed &= check(len(cap["nic_codes"]) == 0, "No NIC (no Udyam)")
    all_passed &= check(len(cap["hsn_codes_transacted"]) == 3, f"HSN from GST: {cap['hsn_codes_transacted']}")
    
    # Buyer geographies — union
    geos = fingerprint["commercial_profile"]["buyer_geographies"]
    all_passed &= check(len(geos) >= 5, f"Union of voice+OCR states: {geos}")
    
    nsic = fingerprint["nsic_preclearance"]
    all_passed &= check("MISSING_UDYAM" in str(nsic["flags"]), f"Flags warn about missing Udyam: {nsic['flags']}")
    
    if all_passed:
        print(f"\n  🎉 TEST 3 PASSED")
    else:
        print(f"\n  ⚠️  TEST 3 HAD FAILURES")
    
    return all_passed, fingerprint


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4: Input validation
# ═══════════════════════════════════════════════════════════════════════════════

def test_input_validation():
    separator("TEST 4: Input Validation")
    merger = FingerprintMerger()
    
    all_passed = True
    
    # Valid inputs
    voice_valid = merger.validate_voice_input(MOCK_VOICE_OUTPUT)
    all_passed &= check(voice_valid["valid"], "Voice output validates OK")
    
    ocr_valid = merger.validate_ocr_input(MOCK_OCR_BOTH)
    all_passed &= check(ocr_valid["valid"], f"OCR output validates OK (errors: {ocr_valid['errors']})")
    
    # Invalid: merge_ready = False
    bad_voice = {**MOCK_VOICE_OUTPUT, "merge_ready": False, "missing_critical_fields": ["enterprise_name"]}
    try:
        merger.merge(bad_voice, MOCK_OCR_BOTH)
        all_passed &= check(False, "Should have raised ValueError for merge_ready=False")
    except ValueError as e:
        all_passed &= check("not merge_ready" in str(e), f"Correct error: {e}")
    
    # Invalid: wrong module
    bad_voice2 = {**MOCK_VOICE_OUTPUT, "module": "wrong_module"}
    v = merger.validate_voice_input(bad_voice2)
    all_passed &= check(not v["valid"], f"Rejects wrong module: {v['errors']}")
    
    if all_passed:
        print(f"\n  🎉 TEST 4 PASSED")
    else:
        print(f"\n  ⚠️  TEST 4 HAD FAILURES")
    
    return all_passed, None


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "█" * 70)
    print("  MSME-Graph Layer 1 Integration Test")
    print("  Testing: OCR ↔ Voice ↔ FingerprintMerger ↔ Schema Validation")
    print("█" * 70)
    
    results = []
    
    passed, fp1 = test_full_merge()
    results.append(("Full Merge (Udyam+GST+Voice)", passed))
    
    passed, fp2 = test_udyam_only_merge()
    results.append(("Udyam-Only + Voice", passed))
    
    passed, fp3 = test_gst_only_merge()
    results.append(("GST-Only + Voice", passed))
    
    passed, _ = test_input_validation()
    results.append(("Input Validation", passed))
    
    # ── Summary ────────────────────────────────────────────────────────────
    separator("RESULTS SUMMARY")
    total = len(results)
    passed_count = sum(1 for _, p in results if p)
    
    for name, p in results:
        icon = "✅" if p else "❌"
        print(f"  {icon}  {name}")
    
    print(f"\n  {passed_count}/{total} test suites passed")
    
    if passed_count == total:
        print("\n  🎉🎉🎉 ALL TESTS PASSED! Layer 1 integration is solid. 🎉🎉🎉")
    else:
        print(f"\n  ⚠️  {total - passed_count} suite(s) failed — check output above")
    
    # ── Print sample fingerprint ───────────────────────────────────────────
    if fp1:
        separator("SAMPLE OUTPUT: Full Merge Fingerprint")
        print(pretty_json(fp1))
    
    sys.exit(0 if passed_count == total else 1)
