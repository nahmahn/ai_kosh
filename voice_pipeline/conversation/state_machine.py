"""
Conversation State Machine — manages the voice onboarding conversation flow.

STATES:
  INITIAL → LISTENING → EXTRACTING → FOLLOWUP_1 → FOLLOWUP_2 → COMPLETE / PARTIAL_COMPLETE

Maximum 2 follow-up rounds. After 2 rounds, accepts partial data and flags
for human review.

Each session is identified by a session_id (UUID4).
"""

import uuid
import time
import logging
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from .followup_questions import (
    get_missing_critical_fields,
    get_all_followup_questions,
)

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):
    INITIAL = "INITIAL"
    LISTENING = "LISTENING"
    EXTRACTING = "EXTRACTING"
    FOLLOWUP_1 = "FOLLOWUP_1"
    FOLLOWUP_2 = "FOLLOWUP_2"
    COMPLETE = "COMPLETE"
    PARTIAL_COMPLETE = "PARTIAL_COMPLETE"


class ConversationSession:
    """
    Represents a single onboarding conversation session.

    Tracks state, accumulated entities, conversation rounds, and timing.
    """

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.state = ConversationState.INITIAL
        self.created_at = datetime.now(timezone.utc)
        self.rounds = 0
        self.max_followups = 6

        # Accumulated data (merged across rounds)
        self.transcripts: List[str] = []
        self.accumulated_entities: Dict[str, Any] = {
            "enterprise_name": None,
            "product_descriptions": [],
            "raw_materials_mentioned": [],
            "manufacturing_process_keywords": [],
            "buyer_types_mentioned": [],
            "buyer_geographies_mentioned": [],
            "production_scale_mentioned": None,
            "years_in_business": None,
            "employees_count": None,
            "existing_online_presence": None,
            "daily_production_capacity": None,
            "factory_area_size": None,
            "major_machinery_used": [],
        }
        self.accumulated_confidence: Dict[str, Any] = {}
        self.audio_metadata: Dict[str, Any] = {}
        self.language: str = "hi"

        # Follow-up tracking
        self.pending_followup_questions: List[Dict[str, str]] = []
        self.missing_fields: List[str] = []

        # Timing
        self.start_time_ms = int(time.time() * 1000)

    def advance_to(self, new_state: ConversationState):
        """Transition to a new state."""
        logger.info(
            "Session %s: %s → %s (round %d)",
            self.session_id,
            self.state.value,
            new_state.value,
            self.rounds,
        )
        self.state = new_state

    def merge_entities(self, new_entities: Dict[str, Any]):
        """
        Merge newly extracted entities into accumulated result.

        - Scalars: new overwrites old only if old is None
        - Lists: union (append unique items)
        """
        for key, new_val in new_entities.items():
            if new_val is None:
                continue
                
            old_val = self.accumulated_entities.get(key)

            if isinstance(new_val, list):
                # Ensure the accumulated value is actually a list before appending
                if old_val is None:
                    self.accumulated_entities[key] = []
                elif not isinstance(old_val, list):
                    # LLM hallucinated a list for a scalar field, or vice versa
                    self.accumulated_entities[key] = [old_val]
                
                existing = set(self.accumulated_entities[key])
                for item in new_val:
                    if item not in existing:
                        self.accumulated_entities[key].append(item)
                        existing.add(item)
            else:
                # Scalar value
                if old_val is None:
                    self.accumulated_entities[key] = new_val

    def merge_confidence(self, new_confidence: Dict[str, Any]):
        """Merge confidence scores — keep the higher value."""
        for key, new_val in new_confidence.items():
            if new_val is None:
                continue
            old_val = self.accumulated_confidence.get(key)
            if old_val is None or new_val > old_val:
                self.accumulated_confidence[key] = new_val

    def add_transcript(self, transcript: str):
        """Add a transcript from a conversation round."""
        if transcript:
            self.transcripts.append(transcript)

    def check_completeness(self) -> bool:
        """
        Check if all critical fields have at least some data.

        Returns True if complete, False if follow-up is needed.
        """
        self.missing_fields = get_missing_critical_fields(self.accumulated_entities)
        return len(self.missing_fields) == 0

    def prepare_followup(self) -> List[Dict[str, str]]:
        """
        Prepare follow-up questions for missing critical fields.

        Returns list of {field, question} dicts.
        """
        self.pending_followup_questions = get_all_followup_questions(
            self.missing_fields, self.language
        )
        return self.pending_followup_questions

    def get_processing_time_ms(self) -> int:
        """Return total processing time in milliseconds."""
        return int(time.time() * 1000) - self.start_time_ms

    @property
    def is_complete(self) -> bool:
        return self.state in (
            ConversationState.COMPLETE,
            ConversationState.PARTIAL_COMPLETE,
        )

    @property
    def is_partial(self) -> bool:
        return self.state == ConversationState.PARTIAL_COMPLETE

    @property
    def full_transcript(self) -> str:
        return " ".join(self.transcripts)


class ConversationManager:
    """
    Manages multiple conversation sessions.

    Provides the main process_audio and process_followup methods
    that drive the state machine.
    """

    def __init__(self):
        self._sessions: Dict[str, ConversationSession] = {}

    def get_session(self, session_id: Optional[str] = None) -> ConversationSession:
        """Get or create a conversation session."""
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]

        session = ConversationSession(session_id)
        self._sessions[session.session_id] = session
        return session

    def has_session(self, session_id: str) -> bool:
        return session_id in self._sessions

    def process_initial_audio(
        self,
        session: ConversationSession,
        stt_result: Dict[str, Any],
        extraction_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process the initial audio submission.

        Steps:
        1. Store transcript + entities
        2. Check completeness
        3. If incomplete → prepare follow-up (FOLLOWUP_1)
        4. If complete → COMPLETE

        Returns the current session state + any follow-up questions.
        """
        session.rounds += 1
        session.advance_to(ConversationState.LISTENING)

        # Store STT result
        session.add_transcript(stt_result.get("cleaned_transcript", ""))
        session.language = stt_result.get("detected_language", "hi")
        session.audio_metadata = {
            "duration_seconds": stt_result.get("duration_seconds", 0.0),
            "language_detected": stt_result.get("detected_language", "hi"),
            "language_confidence": stt_result.get("language_confidence", 0.0),
            "audio_quality_score": stt_result.get("audio_quality", {}).get(
                "quality_score", 0.0
            ),
            "chunks_processed": stt_result.get("chunks_processed", 0),
            "rounds_of_conversation": session.rounds,
        }

        # Store extraction result
        session.advance_to(ConversationState.EXTRACTING)
        entities = extraction_result.get("extracted_entities", {})
        confidence = extraction_result.get("confidence_scores", {})
        session.merge_entities(entities)
        session.merge_confidence(confidence)

        # Check completeness
        if session.check_completeness():
            session.advance_to(ConversationState.COMPLETE)
            return self._build_response(session, followup_questions=[])

        # Needs follow-up
        followup_qs = session.prepare_followup()
        session.advance_to(ConversationState.FOLLOWUP_1)
        return self._build_response(session, followup_questions=followup_qs)

    def process_followup_audio(
        self,
        session: ConversationSession,
        stt_result: Dict[str, Any],
        extraction_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process a follow-up audio submission.

        Same as initial but advances to FOLLOWUP_2 or PARTIAL_COMPLETE.
        """
        session.rounds += 1

        # Store new transcript + entities
        session.add_transcript(stt_result.get("cleaned_transcript", ""))
        session.audio_metadata["rounds_of_conversation"] = session.rounds
        session.audio_metadata["chunks_processed"] += stt_result.get(
            "chunks_processed", 0
        )

        entities = extraction_result.get("extracted_entities", {})
        confidence = extraction_result.get("confidence_scores", {})
        session.merge_entities(entities)
        session.merge_confidence(confidence)

        # Check completeness
        if session.check_completeness():
            session.advance_to(ConversationState.COMPLETE)
            return self._build_response(session, followup_questions=[])

        # Still incomplete
        if session.rounds <= session.max_followups:
            followup_qs = session.prepare_followup()
            session.advance_to(ConversationState.FOLLOWUP_2)
            return self._build_response(session, followup_questions=followup_qs)
        else:
            # Max follow-up rounds reached → partial complete
            session.advance_to(ConversationState.PARTIAL_COMPLETE)
            return self._build_response(session, followup_questions=[])

    def _build_response(
        self,
        session: ConversationSession,
        followup_questions: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Build the response dict for the API layer."""
        return {
            "session_id": session.session_id,
            "state": session.state.value,
            "rounds": session.rounds,
            "language": session.language,
            "accumulated_entities": session.accumulated_entities,
            "accumulated_confidence": session.accumulated_confidence,
            "audio_metadata": session.audio_metadata,
            "full_transcript": session.full_transcript,
            "missing_fields": session.missing_fields,
            "followup_questions": followup_questions,
            "is_complete": session.is_complete,
            "is_partial": session.is_partial,
            "processing_time_ms": session.get_processing_time_ms(),
        }
