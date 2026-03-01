import asyncio
from pathlib import Path
import sys

# Add services dir to path to import engine
sys.path.append(str(Path("/Users/kartiksharma/Desktop/aikosh/services/ocr-engine")))

from engine import ExtractionEngine

async def main():
    engine = ExtractionEngine()
    print("Engine loaded.")
    pdf_path = "/Users/kartiksharma/Desktop/aikosh/samples/udyam_easiofy.pdf"
    
    try:
        result = await engine.process_document(pdf_path, doc_type="udyam")
        print("\nSUCCESS!")
        print(result.model_dump_json(indent=2))
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
