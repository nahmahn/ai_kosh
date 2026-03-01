import os
import time
from fastapi import FastAPI, UploadFile, Form, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="MSME-Graph Voice Pipeline (MOCKED)",
    description="A lightweight placeholder for the ONDC voice onboarding flow.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InitConversationRequest(BaseModel):
    phone_number: str
    language: str

class ProcessAudioResponse(BaseModel):
    session_id: str
    round: int
    transcript: str
    extracted_entities: dict
    missing_fields: list[str]
    followup_questions_audio: list[dict]
    is_complete: bool

@app.get("/voice/health")
async def health_check():
    return {
        "status": "healthy",
        "mode": "MOCKED",
        "description": "Voice pipeline is running in mock mode. No inference is active."
    }

@app.post("/voice/process", response_model=ProcessAudioResponse)
async def process_initial_audio(
    audio: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    language: Optional[str] = Form("hi"),
    current_round: int = Form(0),
):
    """
    Mock endpoint: Always returns a successful extraction of a fictitious MSME.
    """
    # Simulate processing time
    time.sleep(1.5)
    
    # Mock data extraction
    mock_entities = {
        "enterprise_name": "Kiran Manufacturing Works",
        "owner_name": "Kiran Sharma",
        "business_type": "Manufacturing",
        "products_mentioned": ["Handmade Textiles", "Cotton Threads"],
        "buyer_geographies_mentioned": ["Delhi", "Mumbai"],
        "scale": "Micro",
        "is_exporter": False
    }

    return ProcessAudioResponse(
        session_id=session_id or f"mock-session-{int(time.time())}",
        round=current_round + 1,
        transcript="Hello, my name is Kiran Sharma and I run Kiran Manufacturing Works. We make handmade textiles and cotton threads, mostly for Delhi and Mumbai buyers.",
        extracted_entities=mock_entities,
        missing_fields=[],
        followup_questions_audio=[],
        is_complete=True
    )

@app.post("/voice/followup", response_model=ProcessAudioResponse)
async def process_followup_audio(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
    language: str = Form("hi"),
    current_round: int = Form(...),
):
    """
    Mock endpoint: Just echoes the initial mock response since a single upload immediately 'completes' the mocked flow.
    """
    time.sleep(1.0)
    return await process_initial_audio(
        audio=audio,
        session_id=session_id,
        language=language,
        current_round=current_round
    )
