"""
Extraction Engine — orchestrates document processing for Layer 1.
Converts PDFs to images and routes to the appropriate parser.
All document types are wrapped in the VerifiedCapabilityFingerprint schema.
"""

from PIL import Image
import pypdfium2 as pdfium

import os
import sys
import time
import re
from datetime import datetime, timezone
from models import VerifiedCapabilityFingerprint




class ExtractionEngine:
    def __init__(self):
        # Lazy load parsers to save memory and init time
        self.parsers = {}

    def _get_parser(self, doc_type: str):
        if doc_type not in self.parsers:
            if doc_type == "udyam":
                from parsers.udyam_parser import UdyamParser
                self.parsers[doc_type] = UdyamParser()
            elif doc_type == "gst":
                from parsers.gst_parser import GSTParser
                self.parsers[doc_type] = GSTParser()
            elif doc_type == "invoice":
                from parsers.invoice_parser import InvoiceParser
                self.parsers[doc_type] = InvoiceParser()
            elif doc_type == "bank":
                from parsers.bank_statement_parser import BankStatementParser
                self.parsers[doc_type] = BankStatementParser()
        return self.parsers[doc_type]
    
    def classify_document(self, image: Image.Image) -> str:
        """
        Robust heuristic-based document classification using OCR text.
        """
        # We need a temporary LayoutLMv3 engine to get text for classification
        from ocr_engine import LayoutLMv3Engine
        classifier_engine = LayoutLMv3Engine()
        text = classifier_engine.get_ocr_text(image)
        text_lower = text.lower()

        import logging
        logger = logging.getLogger("ocr_api")

        # Scores
        gst_score = 0
        udyam_score = 0

        # GSTR-1 Patterns (High weights)
        if re.search(r"gstr\s*-\s*1", text_lower): gst_score += 10
        if re.search(r"gstr1", text_lower): gst_score += 10
        if re.search(r"table\s*4a", text_lower): gst_score += 5
        if re.search(r"b2b", text_lower): gst_score += 3
        if re.search(r"hsn\s*-\s*wise", text_lower): gst_score += 5
        if re.search(r"outward\s*supplies", text_lower): gst_score += 5

        # Udyam Patterns
        if re.search(r"udyam\s*registration\s*certificate", text_lower): udyam_score += 10
        if re.search(r"nic\s*[25]\s*digit", text_lower): udyam_score += 5
        if re.search(r"major\s*activity", text_lower): udyam_score += 5
        
        # Neutral but common markers
        if re.search(r"udyam\s*-\s*[a-z]{2}\s*-\s*\d{2}", text_lower):
            # Only count as Udyam if it's NOT a GSTR-1
            # GSTR-1 often lists Udyam ID in header
            if gst_score < 5:
                udyam_score += 5
            else:
                logger.info("Found Udyam ID but GSTR-1 markers are stronger. Treating as GSTR-1.")

        logger.info(f"Classification scores -> GST: {gst_score}, Udyam: {udyam_score}")

        if gst_score >= udyam_score and gst_score >= 5:
            logger.info("Classified as: gst")
            return "gst"
        elif udyam_score >= 5:
            logger.info("Classified as: udyam")
            return "udyam"
        
        # Final fallback check for common names
        if "gstin" in text_lower and gst_score >= 1:
            return "gst"

        logger.info("Unclear classification, defaulting to udyam")
        return "udyam"

    def _convert_pdf_to_image(self, pdf_path: str) -> Image.Image:
        pdf = pdfium.PdfDocument(pdf_path)
        page = pdf[0]  # First page
        bitmap = page.render(
            scale=2,  # Increase scale for better OCR (approx 144 DPI)
            rotation=0,
        )
        pil_image = bitmap.to_pil()
        pdf.close()
        return pil_image


    def process_document(self, file_path: str, doc_type: str) -> dict:
        """
        Process a single document and return the full output JSON.
        All document types return the VerifiedCapabilityFingerprint schema.
        """
        if file_path.lower().endswith('.pdf'):
            image = self._convert_pdf_to_image(file_path)
        else:
            image = Image.open(file_path)

        if doc_type == "auto":
            doc_type = self.classify_document(image)

        parser = self._get_parser(doc_type)

        if doc_type == "gst":
            result = parser.parse(image)

            # Wrap in the top-level schema
            output = VerifiedCapabilityFingerprint(
                module="ocr_document_extraction",
                schema_version="1.0.0",
                merge_ready=True,
                generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                processing_time_ms=result.get("processing_time_ms"),
                gstr1=result.get("gstr1"),
                nsic_preclearance=result.get("nsic_preclearance"),
                documents_processed=["gstr1"],
                documents_missing=[],
                partial_data_flag=False,
            )

            # Check if extraction was poor — set flags accordingly
            gstr1_data = result.get("gstr1", {})
            if not gstr1_data.get("hsn_table_rows"):
                output.partial_data_flag = True
            if gstr1_data.get("extraction_confidence", 0) < 0.3:
                output.merge_ready = False

            return output.model_dump()

        elif doc_type == "udyam":
            result = parser.parse(image)

            # Wrap in the top-level schema (same pattern as GST)
            udyam_data = result.get("udyam", {})
            output = VerifiedCapabilityFingerprint(
                module="ocr_document_extraction",
                schema_version="1.0.0",
                merge_ready=True,
                generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                processing_time_ms=result.get("processing_time_ms"),
                udyam=udyam_data,
                nsic_preclearance=result.get("nsic_preclearance"),
                documents_processed=["udyam"],
                documents_missing=[],
                partial_data_flag=False,
            )

            # Check if extraction was poor
            extraction_conf = udyam_data.get("extraction_confidence", 0)
            if extraction_conf < 0.3:
                output.merge_ready = False
            if extraction_conf < 0.5:
                output.partial_data_flag = True

            # Check critical fields
            if not udyam_data.get("udyam_id"):
                output.partial_data_flag = True
            if not udyam_data.get("nic_2digit") and not udyam_data.get("nic_5digit"):
                output.partial_data_flag = True

            return output.model_dump()

        else:
            # Other parsers (invoice, bank) still use the old format
            fingerprint = parser.parse(image)
            return fingerprint.model_dump()
