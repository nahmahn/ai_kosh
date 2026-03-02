"""
MSME-Graph Voice Pipeline — FastAPI Application Entrypoint.

Endpoints:
  POST /voice/process      — process initial audio for STT + NLP extraction
  POST /voice/followup     — process follow-up audio (continues conversation)
  POST /fingerprint/merge  — merge voice + OCR JSON into Verified Capability Fingerprint
  GET  /voice/health       — model load status, GPU/CPU info
"""

import logging
import os
import time
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from dotenv import load_dotenv

# ── Load .env (if exists) ────────────────────────────────────────────────────
load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("voice_pipeline")

# ── Imports from our modules ─────────────────────────────────────────────────
from stt.conformer_wrapper import ConformerWrapper
from nlp.entity_extractor import EntityExtractor
from nlp.manufacturing_detector import ManufacturingDetector
from tts.sarvam_tts import SarvamTTS
from conversation.state_machine import ConversationManager
from output.schema_validator import SchemaValidator
from fingerprint_merger import FingerprintMerger


# ── Application lifespan (model loading at startup) ──────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML models at startup."""
    logger.info("=" * 60)
    logger.info("MSME-Graph Voice Pipeline — Starting up")
    logger.info("=" * 60)

    # Load STT model
    stt = ConformerWrapper.get_instance()
    stt.load_model()

    # Load IndicNER (for ORG/LOC span extraction)
    # EntityExtractor.load_ner_model()

    # Load LaBSE (semantic slot filling — language agnostic)
    # EntityExtractor.load_labse_model()

    # Load MuRIL (zero-shot mfg vs trading classification)
    # ManufacturingDetector.load_muril_model()

    logger.info("=" * 60)
    logger.info("Startup complete. Ready to process requests.")
    logger.info("=" * 60)
    yield
    logger.info("Shutting down MSME-Graph Voice Pipeline.")


# ── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="MSME-Graph Voice Pipeline",
    description=(
        "STT/TTS voice pipeline for MSE onboarding — part of the "
        "IndiaAI Innovation Challenge 2026 ONDC TEAM Initiative."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount Static Frontend ────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")

# ── Shared singletons ────────────────────────────────────────────────────────
conversation_manager = ConversationManager()
schema_validator = SchemaValidator()
mfg_detector = ManufacturingDetector()
tts_engine = SarvamTTS()
merger = FingerprintMerger()

# ── Dynamic Follow-Up Question Templates (weak slot → question per language) ──
FOLLOWUP_TEMPLATES: dict = {
    "raw_material": {
        "hi": "आप किस कच्चे माल से बनाते हैं? जैसे कॉटन, स्टील, लकड़ी?",
        "ta": "நீங்கள் என்ன மூலப்பொருட்கள் பயன்படுத்துகிறீர்கள்?",
        "te": "మీరు ఏ ముడిసరుకులు ఉపయోగిస్తారు?",
        "mr": "तुम्ही कोणत्या कच्च्या मालापासून बनवता?",
        "gu": "તમે કઈ કાચી સામગ્રી વાપરો છો?",
        "bn": "আপনি কোন কাঁচামাল ব্যবহার করেন?",
    },
    "manufacturing_process": {
        "hi": "आपकी फैक्ट्री में कैसे बनाया जाता है? मशीन से या हाथ से?",
        "ta": "உங்கள் தொழிற்சாலையில் எப்படி உற்பத்தி செய்கிறீர்கள்?",
        "te": "మీ కర్మాగారంలో ఎలా తయారు చేస్తారు?",
        "mr": "तुमच्या कारखान्यात कसे बनवले जाते?",
        "gu": "તમારી ફેક્ટ્રીમાં કેવી રીતે બનાવવામાં આવે છે?",
        "bn": "আপনার কারখানায় কীভাবে তৈরি করা হয়?",
    },
    "product_description": {
        "hi": "आप मुख्यतः क्या बनाते हैं? अपने मुख्य उत्पाद बताइए।",
        "ta": "நீங்கள் என்ன தயாரிக்கிறீர்கள்?",
        "te": "మీరు ప్రధానంగా ఏమి తయారు చేస్తారు?",
        "mr": "तुम्ही मुख्यतः काय बनवता?",
        "gu": "તમે મુખ્યત્વે શું બનાવો છો?",
        "bn": "আপনি প্রধানত কী তৈরি করেন?",
    },
}


def _get_followup_question(weak_slots: list, lang: str) -> Optional[str]:
    """Return the most relevant follow-up question for the weakest missing slot."""
    for slot in weak_slots:
        templates = FOLLOWUP_TEMPLATES.get(slot, {})
        q = templates.get(lang) or templates.get("hi")
        if q:
            return q
    return None


# ── Pydantic models for request / response ───────────────────────────────────
class MergeRequest(BaseModel):
    voice_output: dict
    ocr_output: dict


class HealthResponse(BaseModel):
    status: str
    stt_model: dict
    ner_model: dict
    tts_service: dict


# ── POST /voice/process ──────────────────────────────────────────────────────
@app.post("/voice/process")
async def process_voice(
    audio: UploadFile = File(...),
    language_hint: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
):
    """
    Process initial audio for STT transcription and NLP entity extraction.

    Accepts a multipart form with:
      - audio: WAV/MP3/M4A audio file
      - language_hint: (optional) ISO language code, e.g. 'hi', 'ta'
      - session_id: (optional) UUID to track conversation session
    """
    start = time.time()

    try:
        # Read audio bytes
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")

        # Run STT
        stt = ConformerWrapper.get_instance()
        stt_result = stt.transcribe(audio_bytes, language_hint=language_hint)

        if not stt_result.get("raw_transcript"):
            logger.warning("Empty transcript from STT")

        # Run NLP extraction
        extractor = EntityExtractor()
        extraction_result = extractor.extract(
            stt_result.get("cleaned_transcript", ""),
            language=stt_result.get("detected_language", "hi"),
        )

        # Get / create conversation session
        session = conversation_manager.get_session(session_id)

        # Process through state machine
        conv_result = conversation_manager.process_initial_audio(
            session, stt_result, extraction_result
        )

        # Build manufacturing signals using new LLM-extracted schema
        entities = conv_result["accumulated_entities"]
        full_transcript = conv_result.get("full_transcript", "")
        # slot_matches are embedded in extraction_result if LaBSE ran (kept for legacy support)
        slot_matches = getattr(extractor, "_last_slot_matches", {})
        gate3_signals = mfg_detector.compute_gate3_score(
            transcript=full_transcript,
            slot_matches=slot_matches,
            extracted_entities=entities,
        )

        # Generate TTS for follow-up questions (if any)
        followup_audio = []
        conv_lang = conv_result.get("language", "hi")
        # Determine which slots are weak based on the LLM JSON arrays
        weak_slots = []
        if not entities.get("product_descriptions"): weak_slots.append("product_descriptions")
        if not entities.get("selling_channels") and not entities.get("buyer_types_mentioned"):
            weak_slots.append("selling_channels")
        if not entities.get("manufacturing_process_keywords") and gate3_signals.get("voice_mfg_confidence_score", 0.0) < 0.2: 
            weak_slots.append("manufacturing_process_keywords")

        dynamic_question = _get_followup_question(weak_slots, conv_lang)
        raw_followup_questions = conv_result.get("followup_questions", [])
        # Inject dynamic question if state machine didn't produce one
        if not raw_followup_questions and dynamic_question and not conv_result.get("is_complete", False):
            raw_followup_questions = [{"field": weak_slots[0] if weak_slots else "details", "question": dynamic_question}]

        for fq in raw_followup_questions:
            if tts_engine.is_configured:
                tts_result = tts_engine.synthesize(
                    fq["question"],
                    language=conv_lang,
                )
                followup_audio.append(
                    {
                        "field": fq["field"],
                        "question": fq["question"],
                        "audio_base64": tts_result.get("audio_base64", ""),
                        "tts_success": tts_result.get("success", False),
                    }
                )
            else:
                followup_audio.append(
                    {
                        "field": fq["field"],
                        "question": fq["question"],
                        "audio_base64": "",
                        "tts_success": False,
                    }
                )

        # Build voice output JSON
        voice_output = schema_validator.build_voice_output(
            session_id=conv_result["session_id"],
            audio_metadata=conv_result.get("audio_metadata", {}),
            raw_transcript=stt_result.get("raw_transcript", ""),
            cleaned_transcript=session.full_transcript,
            language=conv_result.get("language", "hi"),
            extracted_entities=entities,
            confidence_scores=conv_result.get("accumulated_confidence", {}),
            nsic_gate3_signals=gate3_signals,
            missing_critical_fields=conv_result.get("missing_fields", []),
            conversation_complete=conv_result.get("is_complete", False),
            partial_data_flag=conv_result.get("is_partial", False),
            processing_time_ms=int((time.time() - start) * 1000),
            rounds_of_conversation=conv_result.get("rounds", 1),
        )

        # Validate
        validation = schema_validator.validate(voice_output)
        if not validation["valid"]:
            logger.warning("Output validation issues: %s", validation["errors"])

        # Add follow-up audio and state to the response
        response = {
            **voice_output,
            "conversation_state": conv_result.get("state", "UNKNOWN"),
            "followup_questions_audio": followup_audio,
        }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error processing voice")
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /voice/followup ─────────────────────────────────────────────────────
@app.post("/voice/followup")
async def process_followup(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
    language_hint: Optional[str] = Form(None),
):
    """
    Process follow-up audio for an existing conversation session.

    Requires a session_id from a previous /voice/process call.
    Continues the conversation to fill missing critical fields.
    """
    start = time.time()

    if not conversation_manager.has_session(session_id):
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found. Start with /voice/process first.",
        )

    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")

        # Run STT
        stt = ConformerWrapper.get_instance()
        stt_result = stt.transcribe(audio_bytes, language_hint=language_hint)

        # Run NLP extraction
        extractor = EntityExtractor()
        extraction_result = extractor.extract(
            stt_result.get("cleaned_transcript", ""),
            language=stt_result.get("detected_language", "hi"),
        )

        # Process follow-up in state machine
        session = conversation_manager.get_session(session_id)
        conv_result = conversation_manager.process_followup_audio(
            session, stt_result, extraction_result
        )

        # Build manufacturing signals
        entities = conv_result["accumulated_entities"]
        full_transcript = conv_result.get("full_transcript", "")
        slot_matches = getattr(extractor, "_last_slot_matches", {})
        gate3_signals = mfg_detector.compute_gate3_score(
            transcript=full_transcript,
            slot_matches=slot_matches,
            extracted_entities=entities,
        )

        # Generate TTS for any new follow-up questions
        followup_audio = []
        conv_lang = conv_result.get("language", "hi")
        # Use accumulated entities (not legacy slot_matches) for weak-slot detection
        weak_slots = []
        if not entities.get("product_descriptions"): weak_slots.append("product_descriptions")
        if not entities.get("selling_channels") and not entities.get("buyer_types_mentioned"):
            weak_slots.append("selling_channels")
        if not entities.get("manufacturing_process_keywords") and gate3_signals.get("voice_mfg_confidence_score", 0.0) < 0.2:
            weak_slots.append("manufacturing_process_keywords")
        dynamic_question = _get_followup_question(weak_slots, conv_lang)
        raw_followup_questions = conv_result.get("followup_questions", [])
        if not raw_followup_questions and dynamic_question and not conv_result.get("is_complete", False):
            raw_followup_questions = [{"field": weak_slots[0] if weak_slots else "details", "question": dynamic_question}]

        for fq in raw_followup_questions:
            if tts_engine.is_configured:
                tts_result = tts_engine.synthesize(
                    fq["question"],
                    language=conv_lang,
                )
                followup_audio.append(
                    {
                        "field": fq["field"],
                        "question": fq["question"],
                        "audio_base64": tts_result.get("audio_base64", ""),
                        "tts_success": tts_result.get("success", False),
                    }
                )
            else:
                followup_audio.append(
                    {
                        "field": fq["field"],
                        "question": fq["question"],
                        "audio_base64": "",
                        "tts_success": False,
                    }
                )

        # Build voice output JSON
        voice_output = schema_validator.build_voice_output(
            session_id=conv_result["session_id"],
            audio_metadata=conv_result.get("audio_metadata", {}),
            raw_transcript=session.full_transcript,
            cleaned_transcript=session.full_transcript,
            language=conv_result.get("language", "hi"),
            extracted_entities=entities,
            confidence_scores=conv_result.get("accumulated_confidence", {}),
            nsic_gate3_signals=gate3_signals,
            missing_critical_fields=conv_result.get("missing_fields", []),
            conversation_complete=conv_result.get("is_complete", False),
            partial_data_flag=conv_result.get("is_partial", False),
            processing_time_ms=int((time.time() - start) * 1000),
            rounds_of_conversation=conv_result.get("rounds", 1),
        )

        response = {
            **voice_output,
            "conversation_state": conv_result.get("state", "UNKNOWN"),
            "followup_questions_audio": followup_audio,
        }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error processing follow-up")
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /fingerprint/merge ──────────────────────────────────────────────────
@app.post("/fingerprint/merge")
async def merge_fingerprint(request: MergeRequest):
    """
    Merge voice pipeline output with OCR pipeline output into the
    final Verified Capability Fingerprint.
    """
    try:
        # Validate inputs
        voice_valid = merger.validate_voice_input(request.voice_output)
        if not voice_valid["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid voice output: {voice_valid['errors']}",
            )

        ocr_valid = merger.validate_ocr_input(request.ocr_output)
        if not ocr_valid["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid OCR output: {ocr_valid['errors']}",
            )

        # Merge
        fingerprint = merger.merge(request.voice_output, request.ocr_output)

        # Validate output
        fp_valid = merger.validate_fingerprint(fingerprint)
        if not fp_valid["valid"]:
            logger.warning("Fingerprint validation issues: %s", fp_valid["errors"])

        return fingerprint

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error merging fingerprint")
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /voice/health ─────────────────────────────────────────────────────────
@app.get("/voice/health")
async def health_check():
    """
    Health check endpoint.
    Returns model load status, GPU/CPU info, and TTS configuration status.
    """
    import platform

    stt = ConformerWrapper.get_instance()

    gpu_info = {}
    try:
        import torch

        gpu_info = {
            "cuda_available": torch.cuda.is_available(),
            "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "cuda_device_name": torch.cuda.get_device_name(0)
            if torch.cuda.is_available()
            else None,
        }
    except ImportError:
        gpu_info = {"cuda_available": False, "note": "torch not installed"}

    return {
        "status": "healthy",
        "service": "MSME-Graph Voice Pipeline",
        "version": "1.0.0",
        "platform": {
            "os": platform.system(),
            "python": platform.python_version(),
            "machine": platform.machine(),
        },
        "gpu": gpu_info,
        "models": {
            "stt": stt.get_status(),
            "ner": EntityExtractor.get_status(),
            "muril": ManufacturingDetector.get_status(),
        },
        "tts": tts_engine.get_status(),
        "active_sessions": len(conversation_manager._sessions),
    }


# ── CLI entrypoint ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
    )
