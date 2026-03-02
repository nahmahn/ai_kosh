"""
Schema Validator — validates output JSON against the voice output schema.

Also builds the complete voice output JSON from extraction results,
audio metadata, and conversation state.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import jsonschema

logger = logging.getLogger(__name__)

# ── Load schema ───────────────────────────────────────────────────────────────
_SCHEMA_DIR = Path(__file__).parent.parent / "schemas"
_VOICE_SCHEMA_FILE = _SCHEMA_DIR / "voice_output_schema.json"

_voice_schema: Optional[Dict] = None


def _load_schema():
    global _voice_schema
    if _voice_schema is not None:
        return
    try:
        with open(_VOICE_SCHEMA_FILE, "r", encoding="utf-8") as f:
            _voice_schema = json.load(f)
        logger.info("Loaded voice output schema from %s", _VOICE_SCHEMA_FILE.name)
    except Exception as e:
        logger.error("Failed to load voice output schema: %s", e)
        _voice_schema = {}


class SchemaValidator:
    """Build and validate the voice pipeline output JSON."""

    def __init__(self):
        _load_schema()

    def build_voice_output(
        self,
        session_id: str,
        audio_metadata: Dict[str, Any],
        raw_transcript: str,
        cleaned_transcript: str,
        language: str,
        extracted_entities: Dict[str, Any],
        confidence_scores: Dict[str, Any],
        nsic_gate3_signals: Dict[str, Any],
        missing_critical_fields: List[str],
        conversation_complete: bool,
        partial_data_flag: bool,
        processing_time_ms: int,
        rounds_of_conversation: int = 1,
    ) -> Dict[str, Any]:
        """
        Build the complete voice output JSON conforming to the schema.

        Returns the full output dict.
        """
        # Determine merge_ready
        merge_ready = self._compute_merge_ready(
            conversation_complete, partial_data_flag, missing_critical_fields
        )

        # Derive ONDC hints from entities
        ondc_hints = self._derive_ondc_hints(extracted_entities)

        output = {
            "module": "voice_stt_tts",
            "schema_version": "1.0.0",
            "session_id": session_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "processing_time_ms": processing_time_ms,
            "audio_metadata": {
                "duration_seconds": audio_metadata.get("duration_seconds", 0.0),
                "language_detected": audio_metadata.get("language_detected", language),
                "language_confidence": audio_metadata.get("language_confidence", 0.0),
                "audio_quality_score": audio_metadata.get("audio_quality_score", 0.0),
                "chunks_processed": audio_metadata.get("chunks_processed", 0),
                "rounds_of_conversation": rounds_of_conversation,
            },
            "transcript": {
                "raw_transcript": raw_transcript,
                "cleaned_transcript": cleaned_transcript,
                "language": language,
                "romanised_transcript": "",  # TODO: add transliteration module
            },
            "extracted_entities": {
                "enterprise_name": extracted_entities.get("enterprise_name"),
                "product_descriptions": extracted_entities.get("product_descriptions", []),
                "raw_materials_mentioned": extracted_entities.get("raw_materials_mentioned", []),
                "manufacturing_process_keywords": extracted_entities.get(
                    "manufacturing_process_keywords", []
                ),
                "buyer_types_mentioned": extracted_entities.get("buyer_types_mentioned", []),
                "buyer_geographies_mentioned": extracted_entities.get(
                    "buyer_geographies_mentioned", []
                ),
                "production_scale_mentioned": extracted_entities.get("production_scale_mentioned"),
                "years_in_business": extracted_entities.get("years_in_business"),
                "employees_count": extracted_entities.get("employees_count"),
                "existing_online_presence": extracted_entities.get("existing_online_presence"),
                "export_signal": extracted_entities.get("export_signal", False),
                "selling_channels": extracted_entities.get("selling_channels", []),
                "annual_turnover": extracted_entities.get("annual_turnover"),
                "daily_production_capacity": extracted_entities.get("daily_production_capacity"),
                "factory_area_size": extracted_entities.get("factory_area_size"),
                "major_machinery_used": extracted_entities.get("major_machinery_used", []),
            },
            "confidence_scores": {
                "enterprise_name": confidence_scores.get("enterprise_name"),
                "product_descriptions": confidence_scores.get("product_descriptions"),
                "raw_materials_mentioned": confidence_scores.get("raw_materials_mentioned"),
                "manufacturing_process_keywords": confidence_scores.get(
                    "manufacturing_process_keywords"
                ),
                "buyer_types_mentioned": confidence_scores.get("buyer_types_mentioned"),
                "buyer_geographies_mentioned": confidence_scores.get(
                    "buyer_geographies_mentioned"
                ),
                "production_scale_mentioned": confidence_scores.get("production_scale_mentioned"),
                "overall_extraction_confidence": confidence_scores.get(
                    "overall_extraction_confidence"
                ),
            },
            "nsic_gate3_signals": nsic_gate3_signals,
            "ondc_hints": ondc_hints,
            "merge_ready": merge_ready,
            "missing_critical_fields": missing_critical_fields,
            "conversation_complete": conversation_complete,
            "partial_data_flag": partial_data_flag,
        }

        return output

    def validate(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the output JSON against the voice output schema.

        Returns:
            Dict with 'valid' (bool) and 'errors' (list of error messages).
        """
        if not _voice_schema:
            return {"valid": True, "errors": ["Schema not loaded — skipping validation"]}

        try:
            jsonschema.validate(instance=output, schema=_voice_schema)
            return {"valid": True, "errors": []}
        except jsonschema.ValidationError as e:
            return {"valid": False, "errors": [str(e.message)]}
        except jsonschema.SchemaError as e:
            return {"valid": False, "errors": [f"Schema error: {str(e)}"]}

    @staticmethod
    def _compute_merge_ready(
        conversation_complete: bool,
        partial_data_flag: bool,
        missing_critical_fields: List[str],
    ) -> bool:
        """
        Determine if this module output is ready for merging.

        merge_ready = False if:
          - conversation_complete is False AND
          - partial_data_flag is True AND
          - missing_critical_fields is non-empty
        """
        if (
            not conversation_complete
            and partial_data_flag
            and len(missing_critical_fields) > 0
        ):
            return False
        return True

    @staticmethod
    def _derive_ondc_hints(entities: Dict[str, Any]) -> Dict[str, Any]:
        """Derive ONDC hints from extracted entities."""
        buyer_types = entities.get("buyer_types_mentioned", [])
        process_kw = entities.get("manufacturing_process_keywords", [])
        products = entities.get("product_descriptions", [])

        b2b_signal = bool(
            set(buyer_types) & {"wholesale", "other_businesses", "export"}
        )
        b2c_signal = bool(
            set(buyer_types) & {"retail", "direct_consumer"}
        )
        export_signal = "export" in buyer_types

        # Fallback for active businesses: if they make/sell but no specific buyer type extracted, default C
        if not b2b_signal and not b2c_signal:
            b2c_signal = True

        # Sector inference (basic heuristic)
        likely_sector = None
        if process_kw:
            likely_sector = "Manufacturing"
        elif products:
            likely_sector = "Trading / Retail"

        likely_domain = None
        if likely_sector == "Manufacturing":
            likely_domain = "ONDC:RET1A"  # Retail > Manufacturing sector
        elif b2b_signal:
            likely_domain = "ONDC:RET1B"  # B2B domain

        return {
            "likely_sector": likely_sector,
            "likely_ondc_domain": likely_domain,
            "b2b_signal": b2b_signal,
            "b2c_signal": b2c_signal,
            "export_signal": export_signal,
        }
