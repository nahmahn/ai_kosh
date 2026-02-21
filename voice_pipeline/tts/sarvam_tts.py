"""
Sarvam TTS Wrapper — Text-to-Speech using Sarvam AI API.

Converts text prompts (follow-up questions) to speech audio in Indian languages.
- API endpoint: https://api.sarvam.ai/text-to-speech
- API key from SARVAM_API_KEY environment variable
- Voice selection based on detected language
- Returns base64 WAV audio
"""

import base64
import logging
import os
from typing import Optional, Dict, Any

import requests

logger = logging.getLogger(__name__)

# ── API Configuration ─────────────────────────────────────────────────────────
SARVAM_TTS_ENDPOINT = "https://api.sarvam.ai/text-to-speech"

# Language → voice mapping
VOICE_MAP = {
    "hi": "kavya",
    "ta": "kavitha",
    "te": "shruti",
    "bn": "kavya",
    "mr": "kavya",
    "gu": "kavya",
    "kn": "kavitha",
    "ml": "kavitha",
    "or": "kavya",
    "pa": "kavya",
    "en": "amelia",
}

# Language → ISO code used by Sarvam API
SARVAM_LANG_CODES = {
    "hi": "hi-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "bn": "bn-IN",
    "mr": "mr-IN",
    "gu": "gu-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "or": "or-IN",
    "pa": "pa-IN",
    "en": "en-IN",
}


class SarvamTTS:
    """Wrapper for Sarvam AI Text-to-Speech API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("SARVAM_API_KEY", "")
        if not self.api_key:
            logger.warning(
                "SARVAM_API_KEY not set. TTS will not function. "
                "Set the environment variable SARVAM_API_KEY."
            )

    @property
    def is_configured(self) -> bool:
        """Check if the API key is configured."""
        return bool(self.api_key)

    def synthesize(
        self,
        text: str,
        language: str = "hi",
        voice: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convert text to speech.

        Args:
            text: Text to synthesize.
            language: ISO language code (e.g. 'hi', 'ta', 'te').
            voice: Override voice name. Defaults to language-appropriate voice.

        Returns:
            Dict with keys:
                - audio_base64: base64-encoded WAV audio string
                - language: language code used
                - voice: voice name used
                - success: bool
                - error: error message if any
        """
        if not self.api_key:
            return {
                "audio_base64": "",
                "language": language,
                "voice": voice or "unknown",
                "success": False,
                "error": "SARVAM_API_KEY not configured",
            }

        if voice is None:
            voice = "kavya"

        # Map language code to Sarvam format
        sarvam_lang = SARVAM_LANG_CODES.get(language, "hi-IN")

        payload = {
            "inputs": [text],
            "target_language_code": sarvam_lang,
            "speaker": voice,
            "speech_sample_rate": 16000,
            "enable_preprocessing": True,
            "model": "bulbul:v3",
        }

        headers = {
            "Content-Type": "application/json",
            "api-subscription-key": self.api_key,
        }

        try:
            logger.info(
                "Calling Sarvam TTS: lang=%s, voice=%s, text_len=%d",
                sarvam_lang,
                voice,
                len(text),
            )
            response = requests.post(
                SARVAM_TTS_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                # Sarvam returns audio in the 'audios' field as base64
                audios = data.get("audios", [])
                audio_base64 = audios[0] if audios else ""

                return {
                    "audio_base64": audio_base64,
                    "language": language,
                    "voice": voice,
                    "success": True,
                    "error": None,
                }
            else:
                error_msg = f"Sarvam API error {response.status_code}: {response.text}"
                logger.error(error_msg)
                return {
                    "audio_base64": "",
                    "language": language,
                    "voice": voice,
                    "success": False,
                    "error": error_msg,
                }

        except requests.exceptions.Timeout:
            return {
                "audio_base64": "",
                "language": language,
                "voice": voice,
                "success": False,
                "error": "Sarvam API request timed out",
            }
        except Exception as e:
            error_msg = f"Sarvam TTS error: {str(e)}"
            logger.error(error_msg)
            return {
                "audio_base64": "",
                "language": language,
                "voice": voice,
                "success": False,
                "error": error_msg,
            }

    def get_status(self) -> Dict[str, Any]:
        """Return TTS service status for health endpoint."""
        return {
            "service": "sarvam_tts",
            "configured": self.is_configured,
            "endpoint": SARVAM_TTS_ENDPOINT,
            "api_key_set": bool(self.api_key),
        }
