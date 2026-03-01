import sys
import os
import json

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nlp.entity_extractor import EntityExtractor
from nlp.manufacturing_detector import ManufacturingDetector

import logging
logging.basicConfig(level=logging.INFO)

def test_hindi_ner():
    # Load models (singleton pattern — safe to call multiple times)
    # EntityExtractor.load_ner_model()
    # EntityExtractor.load_labse_model()
    # ManufacturingDetector.load_muril_model()

    extractor = EntityExtractor()

    # Tricky transcript with tokenization and pronoun edge cases
    text_problematic = "मेरे बिजनेस का नाम शर्मा इंटरप्राइज है हम लोग पिछले दस साल से काम कर रहे हैं हमारे पास बीस वर्कर्स हैं जो लगातार फैक्ट्री में काम करते हैं हम कॉटन शर्ट्स और कुर्ता सुनाते हैं हम काॉटन शर्टस और कुताज बनाते हैं हमारी गाज़ियाबाद में ख़ुद की फैक्ट्री है हमारी ख़ुद की वेबसाइट है हम उससे बेचते हैं"
    print(f"\n\nTesting Extracting on problematic transcript: {text_problematic}")
    result_problematic = extractor.extract(text_problematic, "hi")
    print(json.dumps(result_problematic, indent=2, ensure_ascii=False))

    text1 = "मेरा बिजनेस का नाम शर्मा इंटरप्राइज है हम लोग पिछले दस साल से काम कर रहे हैं हमारे पास बीस वर्कर्स हैं जो लगातार फैक्ट्री में काम करते हैं हम कॉटन शॉट से कुर्तास बनाते हैं हमारा मुख्य प्रोडक्ट कॉटन शर्ट्स और कुर्ताज है"
    print(f"\nTesting Extracting on: {text1}")
    result1 = extractor.extract(text1, "hi")
    print(json.dumps(result1, indent=2, ensure_ascii=False))

    text2 = "हमारा मुख्य प्रोडक्ट कॉटन शर्ट्स और कुर्ताज है"
    print(f"\n\nTesting Extracting on: {text2}")
    result2 = extractor.extract(text2, "hi")
    print(json.dumps(result2, indent=2, ensure_ascii=False))

    print("\n\nTesting Gate 3 manufacturing signals for transcript 1...")
    mfg_signals = extractor.mfg_detector.compute_gate3_score(
        transcript=text1,
        extracted_entities=result1.get("extracted_entities"),
    )
    print(json.dumps(mfg_signals, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    test_hindi_ner()
