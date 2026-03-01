"""
Tests for the NLP module — entity extraction, manufacturing detection, and buyer classification.

Tests use sample transcript strings to verify extraction logic without requiring
the actual IndicNER model to be loaded.
"""

import pytest
from nlp.entity_extractor import EntityExtractor
from nlp.manufacturing_detector import ManufacturingDetector


# ── Manufacturing Detector Tests ─────────────────────────────────────────────


class TestManufacturingDetector:
    """Tests for manufacturing_detector.py"""

    def setup_method(self):
        self.detector = ManufacturingDetector()

    def test_detect_hindi_manufacturing_keywords(self):
        """Should detect Hindi manufacturing terms."""
        transcript = "हम बुनाई और सिलाई का काम करते हैं कटाई भी करते हैं"
        keywords = self.detector.detect_manufacturing_keywords(transcript, "hi")
        assert len(keywords) > 0
        assert "weaving" in keywords
        assert "stitching" in keywords
        assert "cutting" in keywords

    def test_detect_english_manufacturing_keywords(self):
        """Should detect English manufacturing terms."""
        transcript = "We do welding and cutting work, also some polishing"
        keywords = self.detector.detect_manufacturing_keywords(transcript, "en")
        assert "welding" in keywords
        assert "cutting" in keywords
        assert "polishing" in keywords

    def test_no_false_positives(self):
        """Random text should not trigger manufacturing keywords."""
        transcript = "I went to the market yesterday to buy some groceries"
        keywords = self.detector.detect_manufacturing_keywords(transcript, "en")
        assert len(keywords) == 0

    def test_detect_trading_keywords_hindi(self):
        """Should detect Hindi trading keywords."""
        transcript = "हम खरीद के बेचना करते हैं wholesale मein लेते हैं"
        keywords = self.detector.detect_trading_keywords(transcript)
        assert len(keywords) > 0

    def test_detect_trading_keywords_english(self):
        """Should detect English trading keywords."""
        transcript = "We are a reseller, we buy and sell imported goods"
        keywords = self.detector.detect_trading_keywords(transcript)
        assert len(keywords) > 0

    def test_classify_buyer_wholesale(self):
        """Wholesale keywords should be classified correctly."""
        transcript = "हम होलसेल में बेचते हैं bulk order लेते हैं"
        types = self.detector.classify_buyer_types(transcript)
        assert "wholesale" in types

    def test_classify_buyer_retail(self):
        """Retail keywords should be classified correctly."""
        transcript = "हमारी दुकान है ग्राहक सीधा आते हैं"
        types = self.detector.classify_buyer_types(transcript)
        assert "retail" in types

    def test_classify_buyer_government(self):
        """Government keywords should be classified correctly."""
        transcript = "सरकारी टेंडर भरते हैं government orders"
        types = self.detector.classify_buyer_types(transcript)
        assert "government" in types

    def test_classify_buyer_export(self):
        """Export keywords should be classified correctly."""
        transcript = "We export to foreign countries"
        types = self.detector.classify_buyer_types(transcript)
        assert "export" in types

    def test_classify_buyer_other_businesses(self):
        """Factory/company keywords → other_businesses."""
        transcript = "हम factory और company को supply करते हैं"
        types = self.detector.classify_buyer_types(transcript)
        assert "other_businesses" in types

    def test_mfg_confidence_full_manufacturer(self):
        """Full manufacturer should get high confidence."""
        score = self.detector.compute_mfg_confidence(
            process_keywords=["welding", "cutting", "polishing"],  # > 2
            raw_materials=["steel", "iron"],  # > 0
            buyer_types=["wholesale", "other_businesses"],  # has wholesale
            trading_keywords_found=[],  # no trading
        )
        assert score == pytest.approx(0.8)  # 0.3 + 0.3 + 0.2

    def test_mfg_confidence_trader(self):
        """Pure trader should get low/zero confidence."""
        score = self.detector.compute_mfg_confidence(
            process_keywords=[],  # no manufacturing
            raw_materials=[],  # no raw materials
            buyer_types=["retail"],
            trading_keywords_found=["buy and sell"],  # trading signal
        )
        assert score == 0.0  # -0.4 but floored at 0

    def test_mfg_confidence_mixed(self):
        """Mixed signals should give moderate confidence."""
        score = self.detector.compute_mfg_confidence(
            process_keywords=["welding", "cutting", "polishing"],
            raw_materials=["steel"],
            buyer_types=["retail"],
            trading_keywords_found=["import"],
        )
        # +0.3 (keywords>2) + 0.3 (materials>0) + 0 (no wholesale) - 0.4 (trading)
        assert score == pytest.approx(0.2)

    def test_mfg_confidence_cap(self):
        """Score should be capped at 1.0."""
        score = self.detector.compute_mfg_confidence(
            process_keywords=["a", "b", "c", "d"],
            raw_materials=["x"],
            buyer_types=["wholesale", "other_businesses"],
            trading_keywords_found=[],
        )
        assert score <= 1.0

    def test_gate3_signals_structure(self):
        """Gate 3 signals should have all required keys."""
        signals = self.detector.build_gate3_signals(
            process_keywords=["welding"],
            raw_materials=["steel"],
            buyer_types=["wholesale"],
            trading_keywords_found=[],
        )
        assert "manufacturing_evidence_found" in signals
        assert "trading_evidence_found" in signals
        assert "process_keywords_count" in signals
        assert "raw_material_signals_count" in signals
        assert "voice_mfg_confidence_score" in signals
        assert "flag_for_human_review" in signals
        assert "flag_reason" in signals

    def test_gate3_ambiguous_flags_review(self):
        """Ambiguous signals should flag for human review."""
        signals = self.detector.build_gate3_signals(
            process_keywords=["welding"],
            raw_materials=["steel"],
            buyer_types=[],
            trading_keywords_found=["import"],  # Both mfg and trading signals
        )
        assert signals["flag_for_human_review"] is True
        assert "ambiguous" in signals["flag_reason"].lower()


# ── Entity Extractor Tests ───────────────────────────────────────────────────


class TestEntityExtractor:
    """Tests for entity_extractor.py (NER model NOT loaded, rule-based only)."""

    def setup_method(self):
        self.extractor = EntityExtractor()

    def test_extract_empty_transcript(self):
        """Empty transcript should return empty entities."""
        result = self.extractor.extract("", "hi")
        entities = result["extracted_entities"]
        assert entities["enterprise_name"] is None
        assert entities["product_descriptions"] == []
        assert entities["raw_materials_mentioned"] == []

    def test_extract_raw_materials_hindi(self):
        """Should detect raw materials in Hindi transcript."""
        transcript = "हम स्टील और लोहा use करते हैं, कपास भी लेते हैं"
        result = self.extractor.extract(transcript, "hi")
        materials = result["extracted_entities"]["raw_materials_mentioned"]
        assert any("स्टील" in m or "steel" in m.lower() for m in materials) or len(materials) > 0

    def test_extract_raw_materials_english(self):
        """Should detect raw materials in English transcript."""
        transcript = "We use cotton and steel as primary raw materials"
        result = self.extractor.extract(transcript, "en")
        materials = result["extracted_entities"]["raw_materials_mentioned"]
        assert "cotton" in materials
        assert "steel" in materials

    def test_extract_geographies(self):
        """Should detect Indian geographies."""
        transcript = "We sell to buyers in Mumbai, Delhi, and Gujarat"
        result = self.extractor.extract(transcript, "en")
        geos = result["extracted_entities"]["buyer_geographies_mentioned"]
        assert "Mumbai" in geos
        assert "Delhi" in geos
        assert "Gujarat" in geos

    def test_extract_geographies_hindi(self):
        """Should detect Hindi geography names."""
        transcript = "हम दिल्ली और मुंबई में बेचते हैं"
        result = self.extractor.extract(transcript, "hi")
        geos = result["extracted_entities"]["buyer_geographies_mentioned"]
        assert len(geos) > 0

    def test_extract_online_presence_positive(self):
        """Should detect online platform mentions."""
        transcript = "We sell on Amazon and Flipkart also have Instagram page"
        result = self.extractor.extract(transcript, "en")
        assert result["extracted_entities"]["existing_online_presence"] is True

    def test_extract_online_presence_negative(self):
        """Transcript without any online platform mention should return None."""
        transcript = "Hum sirf dukaan se bechte hain seedha grahak ko"
        result = self.extractor.extract(transcript, "hi")
        # No online platform mentioned → None (not mentioned)
        assert result["extracted_entities"]["existing_online_presence"] is None

    def test_extract_years_in_business(self):
        """Should extract years of operation."""
        transcript = "We have been operating for 15 years since 2010"
        result = self.extractor.extract(transcript, "en")
        years = result["extracted_entities"]["years_in_business"]
        assert years is not None
        assert years > 0

    def test_extract_employees(self):
        """Should extract employee count."""
        transcript = "We have 25 workers in our factory"
        result = self.extractor.extract(transcript, "en")
        assert result["extracted_entities"]["employees_count"] == 25

    def test_confidence_scores_structure(self):
        """Confidence scores should follow the expected structure."""
        transcript = "We make steel furniture with 10 workers in Mumbai"
        result = self.extractor.extract(transcript, "en")
        confidence = result["confidence_scores"]
        assert "overall_extraction_confidence" in confidence
        assert "enterprise_name" in confidence

    def test_no_hallucination(self):
        """Fields not mentioned should be null/empty, never guessed."""
        transcript = "Hello good morning how are you"
        result = self.extractor.extract(transcript, "en")
        entities = result["extracted_entities"]
        assert entities["enterprise_name"] is None
        assert entities["product_descriptions"] == []
        assert entities["employees_count"] is None
        assert entities["years_in_business"] is None
        assert entities["production_scale_mentioned"] is None

    def test_manufacturing_keywords_detected(self):
        """Manufacturing process keywords should come through."""
        transcript = "We do welding, cutting, and polishing of metal parts"
        result = self.extractor.extract(transcript, "en")
        kw = result["extracted_entities"]["manufacturing_process_keywords"]
        assert len(kw) > 0

    def test_buyer_types_detected(self):
        """Buyer types should be classified."""
        transcript = "We sell wholesale to factories and also export"
        result = self.extractor.extract(transcript, "en")
        types = result["extracted_entities"]["buyer_types_mentioned"]
        assert "wholesale" in types or "export" in types or "other_businesses" in types
