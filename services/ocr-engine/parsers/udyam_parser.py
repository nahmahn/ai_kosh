"""
Udyam Registration Certificate Parser
Model: LayoutLMv3 / OCR (as specified in MSME-Graph proposal Section 3.2)

LayoutLMv3 processor handles OCR internally via Tesseract.
This parser then applies robust regex patterns calibrated against
real Udyam certificate OCR output to extract structured signals.
"""

from PIL import Image
from parsers.base_parser import DocumentParser
from models import VerifiedCapabilityFingerprint, UdyamSignals
from ocr_engine import LayoutLMv3Engine
import re


class UdyamParser(DocumentParser):
    def __init__(self):
        self.engine = LayoutLMv3Engine()

    def parse(self, image: Image.Image) -> VerifiedCapabilityFingerprint:
        features = self.engine.extract_features(image)
        raw_text = features["ocr_text"]

        nic_code = self._extract_nic_code(raw_text)
        district = self._extract_district(raw_text)
        major_activity = self._extract_major_activity(raw_text)
        enterprise_class = self._extract_enterprise_class(raw_text)
        udyam_number = self._extract_udyam_number(raw_text)
        enterprise_name = self._extract_enterprise_name(raw_text)

        signals = UdyamSignals(
            nic_code=nic_code,
            district=district,
            major_activity=major_activity,
            enterprise_class=enterprise_class
        )

        fields = [nic_code, district, major_activity, enterprise_class]
        filled = sum(1 for f in fields if f is not None)
        confidence = round(filled / len(fields), 2)

        return VerifiedCapabilityFingerprint(
            schema_version="1.0.0",
            merge_ready=True,
            udyam={
                **signals.model_dump(),
                "udyam_number": udyam_number,
                "enterprise_name": enterprise_name
            },
            nsic_preclearance={
                "manufacturing_confidence_score": confidence,
                "document_type": "udyam_registration_certificate"
            },
            documents_processed=["udyam_registration_certificate"]
        )

    def _extract_nic_code(self, text: str) -> str | None:
        """
        Extract 5-digit NIC codes from the NIC table in Udyam certificates.
        Real format example: "45200 - Maintenance and repair of motor vehicles"
        """
        # Look for 5-digit NIC codes (most specific)
        five_digit = re.findall(r"\b(\d{5})\b", text)
        if five_digit:
            return five_digit[0]

        # Fallback: look for "NIC 5 Digit" section pattern
        match = re.search(r"NIC\s*5\s*Digit\s+(\d{5})", text, re.IGNORECASE)
        if match:
            return match.group(1)

        # Fallback: look for 4-digit NIC
        four_digit = re.findall(r"\b(\d{4})\b", text)
        if four_digit:
            # Filter out years
            for code in four_digit:
                if not (1900 <= int(code) <= 2100):
                    return code

        return None

    def _extract_district(self, text: str) -> str | None:
        """
        Extract district from the official address section.
        Real format: "DEHRADUN , Pin State UTTARAKHAND 248001"
        or look for known patterns like city names before Pin/State.
        """
        # Pattern 1: "CITY , Pin State STATE PINCODE"
        match = re.search(r"([A-Z]{3,})\s*,?\s*Pin\s*(?:Code)?\s*(?:State)?\s*[A-Z]+\s*\d{6}", text)
        if match:
            return match.group(1).strip().title()

        # Pattern 2: After "Road" keyword, city name often appears
        match = re.search(r"Road\s+([A-Z][A-Za-z\s]+?)\s*,?\s*Pin", text)
        if match:
            return match.group(1).strip().title()

        # Pattern 3: Look for word before a 6-digit pincode
        match = re.search(r"([A-Z]{3,})\s*\d{6}", text)
        if match:
            return match.group(1).strip().title()

        return None

    def _extract_major_activity(self, text: str) -> str | None:
        """
        Extract major activity from the NIC table's Activity column.
        Real format: "45200 - Maintenance and repair | Trading"
        The activity type (Manufacturing/Trading/Services) appears in the Activity column.
        """
        # Look for the Activity column values in NIC table
        activities = re.findall(r"Activity\s+\d*\s*(\w+)", text, re.IGNORECASE)

        # Also look for standalone activity keywords near NIC codes
        text_lower = text.lower()

        # Count occurrences of each activity type in the NIC table
        manufacturing_count = len(re.findall(r"\bmanufacturing\b", text_lower))
        trading_count = len(re.findall(r"\btrading\b", text_lower))
        services_count = len(re.findall(r"\bservice[s]?\b", text_lower))

        counts = {
            "Manufacturing": manufacturing_count,
            "Trading": trading_count,
            "Services": services_count
        }

        # Return the most frequent activity type
        max_activity = max(counts, key=counts.get)
        if counts[max_activity] > 0:
            return max_activity

        return None

    def _extract_enterprise_class(self, text: str) -> str | None:
        """
        Extract enterprise class (Micro/Small/Medium).
        Real format: "MICRO ( Based on FY 2020-21 )"
        """
        match = re.search(r"\b(MICRO|SMALL|MEDIUM)\b", text, re.IGNORECASE)
        if match:
            return match.group(1).capitalize()
        return None

    def _extract_udyam_number(self, text: str) -> str | None:
        """Extract UDYAM registration number like UDYAM-UK-05-0032800"""
        match = re.search(r"(UDYAM-[A-Z]{2}-\d{2}-\d+)", text)
        if match:
            return match.group(1)
        return None

    def _extract_enterprise_name(self, text: str) -> str | None:
        """Extract enterprise name like M/S AVINYA AUTOMOTIVE PRIVATE LIMITED"""
        match = re.search(r"M/[Ss]\s+(.+?)(?:\s+MICRO|\s+SMALL|\s+MEDIUM|\s+Flat|\s+TYPE)", text)
        if match:
            return match.group(1).strip()
        return None
