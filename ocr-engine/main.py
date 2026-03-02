import os
import tempfile
import logging
from dotenv import load_dotenv
load_dotenv()  # Load .env file (GEMINI_API_KEY etc.)

import pytesseract
# Configure Tesseract path as early as possible
tesseract_path = os.getenv("TESSERACT_PATH")
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    print(f"DEBUG: Configured pytesseract.tesseract_cmd to: {pytesseract.pytesseract.tesseract_cmd}")

from fastapi import FastAPI, UploadFile, File, Form, HTTPException

from fastapi.middleware.cors import CORSMiddleware

from engine import ExtractionEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ocr_api")

app = FastAPI(title="AIKosh OCR Engine API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

extraction_engine = ExtractionEngine()

@app.post("/ocr/process")
def process_ocr(
    file: UploadFile = File(...),
    doc_type: str = Form("auto")
):
    try:
        suffix = os.path.splitext(file.filename)[1].lower() if file.filename else ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file.file.read())
            tmp_path = tmp.name

        try:
            logger.info(f"Processing document {file.filename} as type {doc_type}")
            result = extraction_engine.process_document(tmp_path, doc_type=doc_type)
            return result
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as e:
        logger.exception("Error during OCR extraction")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
