"""
Bank Statement Parser
Model: NLP + pattern extraction (as specified in MSME-Graph proposal Section 3.2)

Uses LayoutLMv3's internal OCR for text extraction, then applies
NLP regex patterns to extract financial signals.
"""

from PIL import Image
from parsers.base_parser import DocumentParser
from models import VerifiedCapabilityFingerprint, BankStatementSignals
from ocr_engine import LayoutLMv3Engine
import re


class BankStatementParser(DocumentParser):
    def __init__(self):
        self.engine = LayoutLMv3Engine()

    def parse(self, image: Image.Image) -> VerifiedCapabilityFingerprint:
        # Use LayoutLMv3's internal OCR for text extraction
        raw_text = self.engine.get_ocr_text(image)

        # NLP + pattern extraction
        payment_cycles = self._detect_payment_cycles(raw_text)
        avg_receivables = self._extract_avg_receivables(raw_text)
        seasonal_bands = self._detect_seasonal_bands(raw_text, avg_receivables)

        signals = BankStatementSignals(
            payment_cycles=payment_cycles,
            average_receivables=avg_receivables,
            seasonal_revenue_bands=seasonal_bands
        )

        fields = [payment_cycles, seasonal_bands]
        filled = sum(1 for f in fields if f and f != "Unknown")
        has_receivables = avg_receivables is not None
        confidence = round((filled + int(has_receivables)) / 3, 2)

        return VerifiedCapabilityFingerprint(
            schema_version="1.0.0",
            merge_ready=True,
            manufacturing_confidence_score=confidence,
            document_type="bank_statement",
            extracted_signals=signals.model_dump(),
            metadata={
                "model": "nlp-pattern-extraction",
                "ocr_source": "layoutlmv3-internal-tesseract"
            }
        )

    def _detect_payment_cycles(self, text: str) -> str:
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["salary", "neft", "rtgs", "ecs", "nach"]):
            return "Monthly/Frequent"
        elif "upi" in text_lower:
            return "Daily/Frequent"
        return "Unknown"

    def _extract_avg_receivables(self, text: str) -> float | None:
        credits = re.findall(
            r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:CR|Credit|Cr)",
            text, re.IGNORECASE
        )
        if credits:
            try:
                values = [float(v.replace(",", "")) for v in credits]
                return round(sum(values) / len(values), 2)
            except ValueError:
                pass
        return None

    def _detect_seasonal_bands(self, text: str, avg: float | None) -> str:
        if avg is not None:
            if avg > 100000:
                return "High Revenue"
            elif avg > 25000:
                return "Medium Revenue"
            else:
                return "Low Revenue"
        return "Unknown"
