import os
import json
import google.generativeai as genai
from typing import Dict, Any

from models import GSTR1Signals

class GeminiExtractor:
    """
    Extracts structured JSON from raw OCR text using Gemini 1.5 Flash.
    Strictly enforced against hallucination.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment.")

        genai.configure(api_key=self.api_key)
        
        # We use gemini-2.5-flash as it is extremely capable of structured output
        # Temperature 0.0 forces the most deterministic, grounded responses
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=genai.GenerationConfig(
                temperature=0.0,
                response_mime_type="application/json",
            )
        )

    def parse_gstr1(self, raw_ocr_text: str) -> Dict[str, Any]:
        """
        Parses OCR text into a dictionary matching GSTR1Signals schema.
        """
        
        # Extract the JSON Schema from our Pydantic model
        schema_dict = GSTR1Signals.model_json_schema()
        
        prompt = f"""
You are an extremely strict OCR Data Extraction AI. 
Your ONLY job is to extract values EXACTLY as they appear in the provided OCR text into the provided JSON schema.

CRITICAL RULES (FAILURE RESULTS IN IMMEDIATE REJECTION):
1. **NEVER INVENT, GUESS, OR HALLUCINATE NUMBERS.**
2. If a field's value is not explicitly and clearly visible in the text, you MUST return `null` for it (or an empty array `[]` for lists). 
3. DO NOT PERFORM MATH. Do not calculate ratios or averages yourself if they are not explicitly written. (We will calculate those later in post-processing).
4. For Indian rupee amounts (e.g., "Rs. 1,52,000"), extract as floats (e.g., 152000.0). Remove commas.
5. In Table 12 (HSN Summary), make sure to match the rows exactly as they appear. If no rows exist, return an empty array.

Here is the EXACT JSON Schema you MUST follow:
{json.dumps(schema_dict, indent=2)}

Here is the raw OCR text to extract from:
<OCR_TEXT>
{raw_ocr_text}
</OCR_TEXT>

Return ONLY the raw JSON object matching the schema. No markdown wrapping, no extra text.
"""
        response = self.model.generate_content(prompt)
        
        try:
            # Parse the string response into a Python dictionary
            extracted_data = json.loads(response.text)
            return extracted_data
        except json.JSONDecodeError as e:
            print(f"[GeminiExtractor] Failed to parse JSON: {e}")
            print(f"Raw Gemini Response: {response.text}")
            return {}
