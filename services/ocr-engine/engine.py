"""
Extraction Engine — orchestrates document processing for Layer 1.
Converts PDFs to images and routes to the appropriate parser.
"""

from PIL import Image
from pdf2image import convert_from_path
import os
import sys
import time
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
            else:
                raise ValueError(f"Unknown document type: {doc_type}")
        return self.parsers[doc_type]

    def _convert_pdf_to_image(self, pdf_path: str) -> Image.Image:
        images = convert_from_path(pdf_path, first_page=1, last_page=1)
        if not images:
            raise ValueError("Could not extract image from PDF")
        return images[0]

    def process_document(self, file_path: str, doc_type: str) -> dict:
        """
        Process a single document and return the full output JSON.
        For GST type, returns the Section 5 schema format.
        """
        if file_path.lower().endswith('.pdf'):
            image = self._convert_pdf_to_image(file_path)
        else:
            image = Image.open(file_path)

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
        else:
            # Other parsers still use the old format
            fingerprint = parser.parse(image)
            return fingerprint.model_dump()
