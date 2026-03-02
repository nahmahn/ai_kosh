"""
Udyam Registration Certificate Parser
Model: LayoutLMv3 / OCR (as specified in MSME-Graph proposal Section 3.2)

LayoutLMv3 processor handles OCR internally via Tesseract.
This parser then applies robust regex patterns calibrated against
real Udyam certificate OCR output to extract structured signals.

Returns a dict (NOT VerifiedCapabilityFingerprint) — wrapping is done
by ExtractionEngine, keeping this parser focused on extraction only.
"""

from PIL import Image
from parsers.base_parser import DocumentParser
from models import UdyamSignals
from ocr_engine import LayoutLMv3Engine
import re
import time


class UdyamParser(DocumentParser):
    def __init__(self):
        self.engine = LayoutLMv3Engine()

    def parse(self, image: Image.Image) -> dict:
        """
        Parse a Udyam certificate image and return extraction dict.
        ExtractionEngine wraps this in VerifiedCapabilityFingerprint.
        """
        start = time.time()

        features = self.engine.extract_features(image)
        raw_text = features["ocr_text"]

        # Extract all fields
        nic_5digit = self._extract_nic_5digit(raw_text)
        nic_2digit = nic_5digit[:2] if nic_5digit and len(nic_5digit) >= 2 else self._extract_nic_2digit(raw_text)
        district = self._extract_district(raw_text)
        state = self._extract_state(raw_text)
        major_activity = self._extract_major_activity(raw_text)
        enterprise_class = self._extract_enterprise_class(raw_text)
        udyam_id = self._extract_udyam_number(raw_text)
        enterprise_name = self._extract_enterprise_name(raw_text)
        gstin = self._extract_gstin(raw_text)
        date_of_incorporation = self._extract_date_of_incorporation(raw_text)
        social_category = self._extract_social_category(raw_text)

        # Build UdyamSignals with correct field names
        signals = UdyamSignals(
            udyam_id=udyam_id,
            enterprise_name=enterprise_name,
            nic_2digit=nic_2digit,
            nic_5digit=nic_5digit,
            enterprise_class=enterprise_class,
            major_activity=major_activity,
            district=district,
            state=state,
            gstin_from_udyam=gstin,
            date_of_incorporation=date_of_incorporation,
            social_category=social_category,
        )

        # Compute extraction confidence
        critical_fields = [nic_5digit or nic_2digit, district, major_activity, enterprise_class, udyam_id, enterprise_name]
        filled = sum(1 for f in critical_fields if f is not None)
        confidence = round(filled / len(critical_fields), 2)
        signals.extraction_confidence = confidence

        # Manufacturing confidence from Udyam
        mfg_confidence = 0.0
        if major_activity:
            activity_lower = major_activity.lower()
            if activity_lower == "manufacturing":
                mfg_confidence = 0.9
            elif activity_lower == "services":
                mfg_confidence = 0.4
            elif activity_lower == "trading":
                mfg_confidence = 0.1

        nsic_block = {
            "manufacturing_confidence_score": mfg_confidence,
            "document_type": "udyam_registration_certificate",
            "trading_pattern_detected": major_activity and major_activity.lower() == "trading",
            "nsic_gate3_status": "AUTO_APPROVE" if mfg_confidence >= 0.7 else ("HUMAN_REVIEW" if mfg_confidence >= 0.3 else "AUTO_REJECT"),
            "flag_reason": None if mfg_confidence >= 0.7 else (
                "Trading activity — may not qualify" if mfg_confidence < 0.3
                else "Borderline manufacturing confidence"
            ),
        }

        elapsed_ms = int((time.time() - start) * 1000)

        return {
            "udyam": signals.model_dump(),
            "nsic_preclearance": nsic_block,
            "processing_time_ms": elapsed_ms,
        }

    # ─── NIC Code Extraction ──────────────────────────────────────────────

    def _extract_nic_5digit(self, text: str) -> str | None:
        """
        Extract 5-digit NIC codes from the NIC table in Udyam certificates.
        Real format example: "45200 - Maintenance and repair of motor vehicles"
        """
        # Look for "NIC 5 Digit" section pattern first
        match = re.search(r"NIC\s*5\s*Digit\s+(\d{5})", text, re.IGNORECASE)
        if match:
            return match.group(1)

        # Look for 5-digit NIC codes
        five_digit = re.findall(r"\b(\d{5})\b", text)
        for code in five_digit:
            # Filter out pincodes (6 digits nearby context) and years
            if not (10000 <= int(code) <= 99999 and 19000 <= int(code) <= 21000):
                return code

        return None

    def _extract_nic_2digit(self, text: str) -> str | None:
        """Extract 2-digit NIC division code."""
        match = re.search(r"NIC\s*2\s*Digit\s+(\d{2})", text, re.IGNORECASE)
        if match:
            return match.group(1)

        # Look for "Nic Code" followed by a 2-digit number
        match = re.search(r"Nic\s*Code\s*:?\s*(\d{2})", text, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    # ─── Field Extractors ─────────────────────────────────────────────────

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

        # Pattern 3: "District" or "Dist" label
        match = re.search(r"(?:District|Dist)\s*[:\-]?\s*([A-Za-z\s]+?)(?:\s*,|\s*Pin|\s*State|\s*\d{6})", text, re.IGNORECASE)
        if match:
            return match.group(1).strip().title()

        # Pattern 4: Look for word before a 6-digit pincode
        match = re.search(r"([A-Z]{3,})\s*\d{6}", text)
        if match:
            return match.group(1).strip().title()

        return None

    def _extract_state(self, text: str) -> str | None:
        """
        Extract state name from the address section.
        Real format: "Pin State UTTARAKHAND 248001" or "State: Maharashtra"
        """
        # Pattern 1: "State" label followed by state name
        match = re.search(r"State\s*[:\-]?\s*([A-Z][A-Za-z\s]+?)(?:\s*\d{6}|\s*Pin|\s*$)", text, re.IGNORECASE)
        if match:
            state = match.group(1).strip().title()
            # Filter out obviously wrong matches
            if len(state) > 2 and state.lower() not in ("pin", "code", "india"):
                return state

        # Pattern 2: Look for known Indian state names
        states = [
            "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
            "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
            "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
            "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
            "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
            "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi",
            "Jammu and Kashmir", "Ladakh", "Chandigarh", "Puducherry",
        ]
        text_upper = text.upper()
        for s in states:
            if s.upper() in text_upper:
                return s

        return None

    def _extract_major_activity(self, text: str) -> str | None:
        """
        Extract major activity from the NIC table's Activity column.
        Real format: "45200 - Maintenance and repair | Trading"
        """
        # Look for the Activity column values in NIC table
        text_lower = text.lower()

        # Count occurrences of each activity type
        manufacturing_count = len(re.findall(r"\bmanufacturing\b", text_lower))
        trading_count = len(re.findall(r"\btrading\b", text_lower))
        services_count = len(re.findall(r"\bservice[s]?\b", text_lower))

        counts = {
            "Manufacturing": manufacturing_count,
            "Trading": trading_count,
            "Services": services_count
        }

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

        # Alternative: look for "Name of Enterprise" label
        match = re.search(r"Name\s*(?:of)?\s*Enterprise\s*[:\-]?\s*(.+?)(?:\n|\r|$)", text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if len(name) > 2:
                return name

        return None

    def _extract_gstin(self, text: str) -> str | None:
        """Extract GSTIN from Udyam certificate if present."""
        match = re.search(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z\d][A-Z])\b", text)
        if match:
            return match.group(1)
        return None

    def _extract_date_of_incorporation(self, text: str) -> str | None:
        """
        Extract date of incorporation / commencement.
        Formats: "01/04/2015", "01-04-2015", "1st April 2015"
        """
        # DD/MM/YYYY or DD-MM-YYYY
        match = re.search(
            r"(?:Date\s*of\s*(?:Incorporation|Commencement|Registration|Udyam))\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})",
            text, re.IGNORECASE
        )
        if match:
            return match.group(1)

        return None

    def _extract_social_category(self, text: str) -> str | None:
        """
        Extract social category of the entrepreneur.
        Values: General, SC, ST, OBC, Women
        """
        match = re.search(
            r"(?:Social\s*Category|Category)\s*[:\-]?\s*(General|SC|ST|OBC|Women)",
            text, re.IGNORECASE
        )
        if match:
            return match.group(1).upper() if match.group(1).upper() in ("SC", "ST", "OBC") else match.group(1).capitalize()

        # Look for "Women" enterprise tag
        if re.search(r"\bwomen\s*(?:owned|led|enterprise)\b", text, re.IGNORECASE):
            return "Women"

        return None
