"""
LayoutLMv3-based OCR + Document Understanding Engine for MSME-Graph Layer 1.

LayoutLMv3 (Microsoft) is a multimodal Transformer that jointly models
text, layout (bounding boxes), and document images. It uses Tesseract
internally via its processor for OCR tokenization — we do NOT run
Tesseract separately. This is the approach specified in the MSME-Graph
proposal (Section 3.2 & 7.1).

For e-Invoices, the Donut model is used instead (OCR-free).
"""

from transformers import LayoutLMv3Processor, LayoutLMv3ForSequenceClassification
from PIL import Image
import torch
from typing import List, Dict, Any, Optional


class LayoutLMv3Engine:
    """
    Wraps the LayoutLMv3 processor for document feature extraction.
    The processor internally runs Tesseract OCR to produce:
      - text tokens
      - bounding boxes (layout info)
      - image features
    These are fused by LayoutLMv3 for document understanding.
    """

    def __init__(self):
        model_name = "microsoft/layoutlmv3-base"
        self.processor = LayoutLMv3Processor.from_pretrained(
            model_name, apply_ocr=True  # This tells LayoutLMv3 to use Tesseract internally
        )
        self.model = LayoutLMv3ForSequenceClassification.from_pretrained(model_name)

        self.device = "cpu"
        if torch.cuda.is_available():
            self.device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self.device = "mps"

        self.model.to(self.device)
        self.model.eval()

    def extract_features(self, image: Image.Image) -> Dict[str, Any]:
        """
        Runs LayoutLMv3 processor on a document image.
        Returns the OCR'd words, bounding boxes, and model embeddings.
        """
        image = image.convert("RGB")

        # The processor runs Tesseract internally (apply_ocr=True)
        # and returns: input_ids, attention_mask, bbox, pixel_values
        encoding = self.processor(
            image,
            return_tensors="pt",
            truncation=True,
            max_length=512
        )

        # Extract the raw OCR words and boxes that the processor found
        words = encoding.pop("words", None) if "words" in encoding else None

        # Move tensors to device
        encoding = {k: v.to(self.device) for k, v in encoding.items()}

        # Get model embeddings (hidden states)
        with torch.no_grad():
            outputs = self.model(**encoding, output_hidden_states=True)

        # Return the OCR text, bounding boxes, and embeddings
        result = {
            "last_hidden_state": outputs.hidden_states[-1].cpu(),
        }

        # Also extract raw OCR text from the processor
        # The processor stores OCR results during processing
        raw_ocr = self._extract_ocr_text(image)
        result["ocr_text"] = raw_ocr["text"]
        result["ocr_boxes"] = raw_ocr["boxes"]

        return result

    def _extract_ocr_text(self, image: Image.Image) -> Dict[str, Any]:
        """
        Uses the LayoutLMv3 processor's internal OCR (Tesseract)
        to get raw words and bounding boxes.
        """
        # The processor's image_processor has apply_ocr=True
        # which runs pytesseract.image_to_data internally
        ocr_result = self.processor.image_processor(image)

        words = ocr_result.get("words", [[]])[0] if "words" in ocr_result else []
        boxes = ocr_result.get("boxes", [[]])[0] if "boxes" in ocr_result else []

        full_text = " ".join(words) if words else ""

        return {
            "text": full_text,
            "words": words,
            "boxes": boxes
        }

    def get_ocr_text(self, image: Image.Image) -> str:
        """
        Convenience method: just get the OCR text from a document image,
        using LayoutLMv3's internal Tesseract pipeline.
        """
        result = self._extract_ocr_text(image)
        return result["text"]
