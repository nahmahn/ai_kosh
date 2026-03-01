from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel
import torch
from parsers.base_parser import DocumentParser
from models import VerifiedCapabilityFingerprint, InvoiceSignals
import re

class InvoiceParser(DocumentParser):
    def __init__(self):
        # OCR-free document parser pre-trained on receipts/invoices
        model_name = "naver-clova-ix/donut-base-finetuned-cord-v2"
        self.processor = DonutProcessor.from_pretrained(model_name)
        self.model = VisionEncoderDecoderModel.from_pretrained(model_name)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # On Mac with MPS we could use mps, but cpu/cuda is safer default
        import platform
        if platform.system() == "Darwin" and torch.backends.mps.is_available():
             self.device = "mps"
             
        self.model.to(self.device)

    def parse(self, image: Image.Image) -> VerifiedCapabilityFingerprint:
        # Convert to RGB
        image = image.convert("RGB")
        
        # Prepare inputs
        pixel_values = self.processor(image, return_tensors="pt").pixel_values
        pixel_values = pixel_values.to(self.device)

        # Generate output
        task_prompt = "<s_cord-v2>"
        decoder_input_ids = self.processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="pt").input_ids
        decoder_input_ids = decoder_input_ids.to(self.device)

        outputs = self.model.generate(
            pixel_values,
            decoder_input_ids=decoder_input_ids,
            max_length=self.model.decoder.config.max_position_embeddings,
            pad_token_id=self.processor.tokenizer.pad_token_id,
            eos_token_id=self.processor.tokenizer.eos_token_id,
            use_cache=True,
            bad_words_ids=[[self.processor.tokenizer.unk_token_id]],
            return_dict_in_generate=True,
        )

        sequence = self.processor.batch_decode(outputs.sequences)[0]
        sequence = sequence.replace(self.processor.tokenizer.eos_token, "").replace(self.processor.tokenizer.pad_token, "")
        sequence = re.sub(r"<.*?>", "", sequence, count=1).strip()  # remove first task start token
        
        extracted_data = self.processor.token2json(sequence)
        
        # Map Donut parsed JSON to our Schema
        signals = InvoiceSignals(
            average_order_size=None,
            buyer_geographies=[],
            delivery_patterns="Standard",
            product_categories=[]
        )
        
        # Basic mapping logic from CORD-trained Donut
        if isinstance(extracted_data, dict) and "menu" in extracted_data:
            menu_items = extracted_data["menu"]
            if isinstance(menu_items, list):
                categories = []
                clean_prices = []
                for item in menu_items:
                    if isinstance(item, dict):
                        if "nm" in item and item["nm"]:
                            categories.append(str(item["nm"]))
                        if "price" in item:
                            try:
                                clean_prices.append(float(str(item["price"]).replace(",", "").replace("$", "")))
                            except:
                                pass
                
                if categories:
                    signals.product_categories = categories
                if clean_prices:
                    signals.average_order_size = float(sum(clean_prices) / len(clean_prices))

        return VerifiedCapabilityFingerprint(
            schema_version="1.0.0",
            merge_ready=True,
            manufacturing_confidence_score=0.90,
            document_type="e_invoice_eway_bill",
            extracted_signals=signals.model_dump(),
            metadata={"model": "donut-base", "raw_output": str(extracted_data)}
        )
