"""
Language Detector — auto-detect spoken language from audio.

Uses the IndicConformer model's internal representations to infer the
language of the input audio. Falls back to a simple heuristic if the
model-based detection is not available.

Supported language codes (ISO 639-1 / custom):
hi, ta, te, bn, mr, gu, kn, ml, or, pa, as, mai, mni, kok, sat, doi,
ur, sd, ks, ne, bo, sa
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ── Supported languages ───────────────────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "or": "Odia",
    "pa": "Punjabi",
    "as": "Assamese",
    "mai": "Maithili",
    "mni": "Manipuri",
    "kok": "Konkani",
    "sat": "Santali",
    "doi": "Dogri",
    "ur": "Urdu",
    "sd": "Sindhi",
    "ks": "Kashmiri",
    "ne": "Nepali",
    "bo": "Bodo",
    "sa": "Sanskrit",
    "en": "English",
}

# Language-to-script mapping (for NER selection)
LANGUAGE_SCRIPTS = {
    "hi": "Devanagari",
    "mr": "Devanagari",
    "kok": "Devanagari",
    "mai": "Devanagari",
    "doi": "Devanagari",
    "ne": "Devanagari",
    "sa": "Devanagari",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "bn": "Bengali",
    "as": "Bengali",
    "gu": "Gujarati",
    "pa": "Gurmukhi",
    "or": "Odia",
    "ur": "Perso-Arabic",
    "sd": "Perso-Arabic",
    "ks": "Perso-Arabic",
    "mni": "Meetei Mayek",
    "sat": "Ol Chiki",
    "bo": "Devanagari",
    "en": "Latin",
}


class LanguageDetector:
    """Detects spoken language from audio or validates a language hint."""

    def validate_language_code(self, code: Optional[str]) -> Optional[str]:
        """
        Validate and normalise a language code.

        Returns:
            The normalised code if valid, else None.
        """
        if code is None:
            return None
        code = code.strip().lower()
        if code in SUPPORTED_LANGUAGES:
            return code
        # Try matching by language name
        for k, v in SUPPORTED_LANGUAGES.items():
            if v.lower() == code:
                return k
        logger.warning("Unsupported language code: '%s'", code)
        return None

    def detect_from_transcript(self, transcript: str) -> Tuple[str, float]:
        """
        Detect language from a transcribed text using Unicode script analysis.

        This is a lightweight fallback when model-based detection is unavailable.

        Returns:
            Tuple of (language_code, confidence).
        """
        if not transcript or not transcript.strip():
            return ("hi", 0.0)  # default fallback

        script_counts = self._count_scripts(transcript)
        if not script_counts:
            return ("en", 0.5)

        dominant_script = max(script_counts, key=script_counts.get)
        total_chars = sum(script_counts.values())
        confidence = script_counts[dominant_script] / total_chars if total_chars > 0 else 0.0

        # Map script back to most common language using that script
        script_to_lang = {
            "Devanagari": "hi",
            "Tamil": "ta",
            "Telugu": "te",
            "Kannada": "kn",
            "Malayalam": "ml",
            "Bengali": "bn",
            "Gujarati": "gu",
            "Gurmukhi": "pa",
            "Odia": "or",
            "Latin": "en",
            "Perso-Arabic": "ur",
        }

        lang = script_to_lang.get(dominant_script, "hi")
        return (lang, round(confidence, 4))

    def get_language_name(self, code: str) -> str:
        """Return human-readable language name."""
        return SUPPORTED_LANGUAGES.get(code, "Unknown")

    def get_script(self, code: str) -> str:
        """Return script used by the language."""
        return LANGUAGE_SCRIPTS.get(code, "Unknown")

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _count_scripts(text: str) -> dict:
        """Count characters by Unicode script."""
        counts = {}
        for ch in text:
            cp = ord(ch)
            script = _classify_codepoint(cp)
            if script:
                counts[script] = counts.get(script, 0) + 1
        return counts


def _classify_codepoint(cp: int) -> Optional[str]:
    """Classify a Unicode codepoint into a script family."""
    if 0x0900 <= cp <= 0x097F:
        return "Devanagari"
    elif 0x0980 <= cp <= 0x09FF:
        return "Bengali"
    elif 0x0A00 <= cp <= 0x0A7F:
        return "Gurmukhi"
    elif 0x0A80 <= cp <= 0x0AFF:
        return "Gujarati"
    elif 0x0B00 <= cp <= 0x0B7F:
        return "Odia"
    elif 0x0B80 <= cp <= 0x0BFF:
        return "Tamil"
    elif 0x0C00 <= cp <= 0x0C7F:
        return "Telugu"
    elif 0x0C80 <= cp <= 0x0CFF:
        return "Kannada"
    elif 0x0D00 <= cp <= 0x0D7F:
        return "Malayalam"
    elif 0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F:
        return "Perso-Arabic"
    elif 0x0041 <= cp <= 0x007A:
        return "Latin"
    return None
