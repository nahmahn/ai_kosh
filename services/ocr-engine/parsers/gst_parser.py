"""
GSTR-1 Parser — Full field extraction per OCR Module Brief Section 3.2

Extracts:
  - Header fields (GSTIN, financial year, tax period, filing date, turnovers)
  - Table 4A (B2B invoices) → computed fields
  - Table 7A (B2C) → computed fields
  - B2B/B2C ratio
  - Table 12 (HSN Summary) → every row as HSNRow (MOST CRITICAL)
  - Manufacturing confidence score via HSN classification
  - NSIC preclearance status

Primary OCR: LayoutLMv3 + Tesseract (offline, no API key needed)
"""

import re
from PIL import Image
from typing import Dict, Any, List, Optional, Tuple

from parsers.base_parser import DocumentParser
from models import (
    VerifiedCapabilityFingerprint, GSTR1Signals, HSNRow,
    NSICPreclearance
)
from ocr_engine import LayoutLMv3Engine
from extractors.hsn_classifier import (
    classify_chapter, detect_trading_pattern,
    compute_manufacturing_confidence, get_nsic_gate3_status
)


class GSTParser(DocumentParser):
    def __init__(self):
        # Primary: LayoutLMv3 + Tesseract (offline)
        self.engine = LayoutLMv3Engine()

        # Track which OCR was used for metadata
        self._ocr_source = "unknown"
        
        # Extractor: Gemini 1.5 Flash (Strict JSON parsing from raw text)
        from extractors.gemini_extractor import GeminiExtractor
        self.gemini = GeminiExtractor()

    def parse(self, image: Image.Image, pdf_path: str = None) -> dict:
        """Parse a GSTR-1 document image and return the full extraction dict."""
        import time
        start = time.time()

        # Step 1: OCR
        raw_text = self._get_ocr_text(image, pdf_path)

        # Step 2: Extract all fields using Gemini
        print("[GSTParser] Passing OCR text to Gemini 1.5 Flash for JSON extraction...")
        gstr1_data = self.gemini.parse_gstr1(raw_text)

        # Step 3: Compute B2B/B2C ratios securely in Python (Preventing LLM math hallucination)
        b2b_total = gstr1_data.get("b2b_total_taxable_value", 0.0) or 0.0
        b2c_total = gstr1_data.get("b2c_total_taxable_value", 0.0) or 0.0
        total = b2b_total + b2c_total

        b2b_ratio = round(b2b_total / total, 2) if total > 0 else None
        b2c_ratio = round(b2c_total / total, 2) if total > 0 else None
        
        gstr1_data["b2b_ratio"] = b2b_ratio
        gstr1_data["b2c_ratio"] = b2c_ratio

        # Handle HSN rows
        hsn_rows = gstr1_data.get("hsn_table_rows", [])
        
        # Step 4: Compute summary fields from HSN table
        hsn_codes_transacted = list(set(r.get("hsn_code", "") for r in hsn_rows if r.get("hsn_code")))
        gstr1_data["hsn_codes_transacted"] = hsn_codes_transacted

        annual_turnover = gstr1_data.get("turnover_previous_fy") or gstr1_data.get("turnover_current_ytd")
        gstr1_data["annual_turnover_inr"] = annual_turnover
        
        # If Gemini didn't calculate avg invoice value but gave us the total and count
        if gstr1_data.get("b2b_avg_invoice_value") is None and b2b_total > 0 and gstr1_data.get("b2b_invoice_count"):
            avg = round(b2b_total / gstr1_data["b2b_invoice_count"], 1)
            gstr1_data["b2b_avg_invoice_value"] = avg
            gstr1_data["avg_invoice_value_inr"] = avg

        # Step 5: Extraction confidence — how many fields did we actually get?
        all_fields = [
            gstr1_data.get("gstin"), gstr1_data.get("financial_year"), gstr1_data.get("tax_period"),
            gstr1_data.get("turnover_previous_fy"), b2b_total > 0, len(hsn_rows) > 0,
            b2b_ratio is not None
        ]
        filled = sum(1 for f in all_fields if f)
        extraction_confidence = round(filled / len(all_fields), 2)
        gstr1_data["extraction_confidence"] = extraction_confidence

        # Step 6: Manufacturing confidence (Section 4 algorithm)
        hsn_row_dicts = [{"hsn_code": r.get("hsn_code", "")} for r in hsn_rows]
        mfg_score = compute_manufacturing_confidence(hsn_row_dicts, b2b_ratio) if hsn_rows else 0.0
        trading_detected, _ = detect_trading_pattern(hsn_row_dicts) if hsn_rows else (False, set())
        raw_found = any(classify_chapter(r.get("hsn_code", "")[:2]) == "RAW_MATERIAL" for r in hsn_rows if r.get("hsn_code"))
        finished_found = any(classify_chapter(r.get("hsn_code", "")[:2]) == "FINISHED_GOOD" for r in hsn_rows if r.get("hsn_code"))
        nsic_status = get_nsic_gate3_status(mfg_score)

        # Determine flag reason
        flag_reason = None
        if nsic_status == "AUTO_REJECT":
            flag_reason = "Low manufacturing confidence — likely a trader"
        elif nsic_status == "HUMAN_REVIEW":
            flag_reason = "Borderline manufacturing confidence — needs manual verification"
        if trading_detected:
            flag_reason = "Trading pattern detected — same HSN chapter in raw and finished"

        elapsed_ms = int((time.time() - start) * 1000)

        # Build NSIC preclearance block
        nsic_block = {
            "manufacturing_confidence_score": mfg_score,
            "trading_pattern_detected": trading_detected,
            "raw_material_hsn_found": raw_found,
            "finished_good_hsn_found": finished_found,
            "nsic_gate3_status": nsic_status,
            "flag_reason": flag_reason,
        }

        return {
            "gstr1": gstr1_data,
            "nsic_preclearance": nsic_block,
            "processing_time_ms": elapsed_ms,
            "ocr_source": self._ocr_source,
        }

    # ─── OCR Strategy ─────────────────────────────────────────────────────

    def _get_ocr_text(self, image: Image.Image, pdf_path: str = None) -> str:
        """
        Get OCR text using LayoutLMv3 + Tesseract.
        """
        self._ocr_source = "layoutlmv3-tesseract"
        features = self.engine.extract_features(image)
        return features["ocr_text"]

    # ─── Header Field Extraction ──────────────────────────────────────────

    def _extract_header_fields(self, text: str) -> Dict[str, Any]:
        """Extract GSTIN, financial year, tax period, filing date, turnovers."""
        result = {}

        # GSTIN — 15 character alphanumeric, starts with 2-digit state code
        gstin_match = re.search(r'\b(\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z\d][A-Z])\b', text)
        if gstin_match:
            result["gstin"] = gstin_match.group(1)

        # Financial Year — pattern like "2024-25" or "2024-2025"
        fy_match = re.search(r'Financial\s*Year[:\s]*(\d{4}[-–]\d{2,4})', text, re.IGNORECASE)
        if fy_match:
            result["financial_year"] = fy_match.group(1)

        # Tax Period — "October 2024" style
        tp_match = re.search(
            r'Tax\s*Period[:\s]*((?:January|February|March|April|May|June|July|August|September|October|November|December)\s*\d{4})',
            text, re.IGNORECASE
        )
        if tp_match:
            result["tax_period"] = tp_match.group(1)

        # Filing Date — from "Date of Filing" or date near ARN
        fd_match = re.search(r'(?:Date\s*of\s*Filing|Filing)[:\s]*(\d{1,2}[-/]\w{3}[-/]\d{4})', text, re.IGNORECASE)
        if fd_match:
            result["filing_date"] = fd_match.group(1)

        # Turnover preceding FY — parse from "Rs. X,XX,XXX/-" or just numbers
        turnover_prev = re.search(
            r'preceding\s*Financial\s*Year.*?Rs\.?\s*([\d,]+)',
            text, re.IGNORECASE | re.DOTALL
        )
        if turnover_prev:
            result["turnover_previous_fy"] = self._parse_rupee_amount(turnover_prev.group(1))

        # Turnover current YTD
        turnover_curr = re.search(
            r'(?:April\s*to|Current\s*Year).*?Rs\.?\s*([\d,]+)',
            text, re.IGNORECASE | re.DOTALL
        )
        if turnover_curr:
            result["turnover_current_ytd"] = self._parse_rupee_amount(turnover_curr.group(1))

        return result

    # ─── Table 4A — B2B Invoice Fields ────────────────────────────────────

    def _extract_b2b_fields(self, text: str) -> Dict[str, Any]:
        """Extract computed fields from Table 4A (B2B Registered Persons)."""
        result = {}

        # Find the B2B section: starts at 4A, ends at 7A or similar
        b2b_section = re.search(
            r'(?:4A[.\s]|Registered\s*Persons?.*?B2B)(.+?)(?:7A[.\s]|Unregistered|12\.|HSN)',
            text, re.IGNORECASE | re.DOTALL
        )

        if b2b_section:
            section_text = b2b_section.group(1)

            # Extract buyer states — pattern like "Gujarat (24)", "Maharashtra (27)"
            # Also catch cases where state name and code are on different words
            states = re.findall(r'([A-Za-z]+)\s*\(\d{1,2}\)', section_text)
            # Also look for full state names preceded by their code
            states2 = re.findall(r'(?:Gujarat|Maharashtra|Karnataka|Haryana|Tamil Nadu|Rajasthan|Delhi|Uttar Pradesh|Kerala|Andhra Pradesh|Telangana|West Bengal|Bihar|Madhya Pradesh|Punjab)', section_text, re.IGNORECASE)
            all_states = set(s for s in states if len(s) > 2) | set(states2)
            result["b2b_buyer_states"] = list(all_states)

            # Count invoices — look for invoice number patterns like RT/24-25/1X
            # Each unique invoice line has the pattern with a date like XX-Oct-24
            inv_dates = re.findall(r'\d{1,2}-\w{3}-\d{2,4}', section_text)
            result["b2b_invoice_count"] = len(inv_dates) if inv_dates else None

            # TOTAL row — find "TOTAL" then grab the first Indian-format number
            # OCR gives us: TOTAL 9,00,000 86,400 10,800 10,800
            total_match = re.search(r'TOTAL\s+([\d,]+)', section_text, re.IGNORECASE)
            if total_match:
                total_val = self._parse_rupee_amount(total_match.group(1))
                if total_val and total_val >= 10000:
                    result["b2b_total_taxable_value"] = total_val

            if result.get("b2b_total_taxable_value") and result.get("b2b_invoice_count"):
                result["b2b_avg_invoice_value"] = round(
                    result["b2b_total_taxable_value"] / result["b2b_invoice_count"], 1
                )

        return result

    # ─── Table 7A — B2C Fields ────────────────────────────────────────────

    def _extract_b2c_fields(self, text: str) -> Dict[str, Any]:
        """Extract B2C total from Table 7A."""
        result = {}

        # Find the B2C section: starts at 7A, ends at Table 12 / HSN
        b2c_section = re.search(
            r'(?:7A[.\s]|Unregistered\s*Persons?.*?B2C)(.+?)(?:12\.|HSN)',
            text, re.IGNORECASE | re.DOTALL
        )

        if b2c_section:
            section_text = b2c_section.group(1)
            # Look for "Total" followed by a number (Indian format)
            total_match = re.search(r'Total\s+([\d,]+)', section_text, re.IGNORECASE)
            if total_match:
                val = self._parse_rupee_amount(total_match.group(1))
                if val and val >= 1000:
                    result["b2c_total_taxable_value"] = val

        return result

    # ─── Table 12 — HSN Summary (MOST CRITICAL) ──────────────────────────

    def _extract_hsn_table(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract every row from Table 12 (HSN-wise Summary).
        This is THE most important table — it tells us WHAT the MSE actually
        produces and sells. Manufacturing confidence is computed entirely from this.
        """
        rows = []

        # Find Table 12 / HSN section
        hsn_section = re.search(
            r'(?:12\.|HSN[-\s]*wise\s*Summary|HSN[-\s]*Code)(.+?)$',
            text, re.IGNORECASE | re.DOTALL
        )

        if not hsn_section:
            return self._fallback_hsn_extraction(text)

        section_text = hsn_section.group(1)

        # Strategy: find all 4-digit HSN codes followed by a UQC somewhere
        # then extract numbers after the UQC.
        # The OCR text for a row looks like:
        #   "1 5208 containing >=85% by weight of MTR 3,200 6,40,000 5,48,000 52,608 8,220 8,220"
        #   "3 5513 MTR 950 1,52,000 1,30,000 12,480 1,950 1,950"
        # Key insight: each row has a 4-digit HSN code, then a UQC, then numbers

        uqc_list = r'(?:MTR|KGS|NOS|PCS|LTR|SQM|CBM|TON|GMS|PAC|OTH)'

        # Find each HSN row: HSN code ... UQC ... qty ... total_value ... taxable_value
        hsn_pattern = re.findall(
            r'\b(\d{4})\b'
            r'(.+?)'
            rf'({uqc_list})'
            r'\s+([\d,]+(?:\.\d+)?)'
            r'\s+([\d,]+(?:\.\d+)?)'
            r'\s+([\d,]+(?:\.\d+)?)',
            section_text, re.IGNORECASE
        )

        for match in hsn_pattern:
            hsn_code, desc, uqc, qty_str, val1_str, val2_str = match
            # Filter out years and non-HSN numbers
            if 1900 <= int(hsn_code) <= 2100:
                continue
            # Clean up description: remove leading/trailing junk
            desc_clean = re.sub(r'^[\s.,;:]+|[\s.,;:]+$', '', desc)
            desc_clean = desc_clean.strip()

            qty = self._parse_rupee_amount(qty_str) or 0.0
            total_value = self._parse_rupee_amount(val1_str) or 0.0
            taxable_value = self._parse_rupee_amount(val2_str) or 0.0

            rows.append({
                "hsn_code": hsn_code,
                "description": desc_clean,
                "uqc": uqc.upper(),
                "total_qty": qty,
                "total_value": total_value,
                "taxable_value": taxable_value,
                "tax_rate_pct": 0.0,
            })

        if not rows:
            return self._fallback_hsn_extraction(text)

        # Compute tax_rate_pct from taxable_value and the tax amount that follows it
        # Don't use % pattern matching — descriptions contain things like ">=85%" which are false positives
        for row in rows:
            if row["taxable_value"] > 0:
                # Try to find the IGST/CGST/SGST amount after the taxable_value
                # In the OCR, after taxable_value there's a total tax amount
                taxable_str = str(int(row["taxable_value"]))
                # Handle Indian-format: 548000 might appear as 5,48,000 in OCR
                tax_match = re.search(
                    rf'{re.escape(taxable_str)}\s+([\d,]+)',
                    section_text
                )
                if tax_match:
                    tax_amount = self._parse_rupee_amount(tax_match.group(1))
                    if tax_amount and tax_amount > 0:
                        rate = round((tax_amount / row["taxable_value"]) * 100, 1)
                        if rate <= 28:  # GST rates are 0, 5, 12, 18, or 28%
                            row["tax_rate_pct"] = rate

        return rows

    def _fallback_hsn_extraction(self, text: str) -> List[Dict[str, Any]]:
        """
        Fallback: extract HSN codes from anywhere in the document.
        Less precise but ensures we get SOMETHING for the confidence score.
        """
        rows = []
        # Find 4-digit numbers that are likely HSN codes
        potential_codes = re.findall(r'\b(\d{4})\b', text)
        seen = set()
        for code in potential_codes:
            code_int = int(code)
            # Filter: not a year, not obviously a non-HSN number
            if 1900 <= code_int <= 2100:
                continue
            if code_int < 100:  # Too small
                continue
            # Check if first 2 digits map to a known HSN chapter
            chapter = code[:2]
            from extractors.hsn_classifier import RAW_MATERIAL_CHAPTERS, FINISHED_GOOD_CHAPTERS
            if chapter in RAW_MATERIAL_CHAPTERS or chapter in FINISHED_GOOD_CHAPTERS:
                if code not in seen:
                    seen.add(code)
                    rows.append({
                        "hsn_code": code,
                        "description": "",
                        "uqc": "",
                        "total_qty": 0.0,
                        "total_value": 0.0,
                        "taxable_value": 0.0,
                        "tax_rate_pct": 0.0,
                    })
        return rows

    # ─── Utilities ────────────────────────────────────────────────────────

    def _parse_rupee_amount(self, text: str) -> Optional[float]:
        """Parse Indian-format rupee amounts like '1,82,45,000' or '98,34,500'."""
        if not text:
            return None
        cleaned = text.replace(",", "").replace("/-", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
