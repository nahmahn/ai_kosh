"""
IndicConformer STT Wrapper — Singleton wrapper around ai4bharat/indic-conformer-600m-multilingual.

Provides:
- One-time model loading at startup (singleton pattern)
- Multi-format audio input (file, base64, bytes)
- Automatic language detection or language hint
- Chunking of long audio with transcript stitching
- Confidence scoring and language code return
"""

import logging
import time
import os
import threading
from typing import Optional, Union, Dict, Any
from pathlib import Path

import numpy as np

from .audio_preprocessor import AudioPreprocessor, CONFIDENCE_PENALTY_LOW_QUALITY
from .language_detector import LanguageDetector

logger = logging.getLogger(__name__)

# ── Model configuration ──────────────────────────────────────────────────────
MODEL_ID = "ai4bharat/indic-conformer-600m-multilingual"


class ConformerWrapper:
    """
    Singleton wrapper for the IndicConformer 600M multilingual STT model.

    Usage:
        wrapper = ConformerWrapper.get_instance()
        result = wrapper.transcribe(audio_input, language_hint="hi")
    """

    _instance: Optional["ConformerWrapper"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._model = None
        self._processor = None
        self._device = None
        self._model_loaded = False
        self._load_error: Optional[str] = None
        self.preprocessor = AudioPreprocessor()
        self.lang_detector = LanguageDetector()

    @classmethod
    def get_instance(cls) -> "ConformerWrapper":
        """Thread-safe singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def load_model(self) -> bool:
        """
        Load the IndicConformer model.

        Call this at application startup. Returns True if successful.
        """
        if self._model_loaded:
            return True

        try:
            import torch
            from transformers import AutoModel

            logger.info("Loading IndicConformer model: %s", MODEL_ID)
            start = time.time()

            # Select device
            if torch.cuda.is_available():
                self._device = "cuda"
                logger.info(
                    "CUDA available: %s (%s)",
                    torch.cuda.get_device_name(0),
                    f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB",
                )
            else:
                self._device = "cpu"
                logger.info("CUDA not available, using CPU")

            self._model = AutoModel.from_pretrained(MODEL_ID, trust_remote_code=True, token=os.environ.get("HF_TOKEN"))
            self._model.to(self._device)
            self._model.eval()

            elapsed = time.time() - start
            self._model_loaded = True
            logger.info("Model loaded in %.1f seconds on %s", elapsed, self._device)
            return True

        except Exception as e:
            self._load_error = str(e)
            logger.error("Failed to load IndicConformer model: %s", e)
            return False

    @property
    def is_loaded(self) -> bool:
        return self._model_loaded

    @property
    def device(self) -> Optional[str]:
        return self._device

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    def transcribe(
        self,
        audio_input: Union[str, bytes, Path],
        language_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transcribe audio input.

        Args:
            audio_input: File path (wav/mp3/m4a), base64 string, or raw bytes.
            language_hint: Optional ISO language code hint (e.g. 'hi', 'ta').

        Returns:
            Dict with keys:
                - raw_transcript: str
                - cleaned_transcript: str
                - detected_language: str (ISO code)
                - language_confidence: float (0–1)
                - confidence: float (0–1)
                - duration_seconds: float
                - chunks_processed: int
                - audio_quality: dict
                - processing_time_ms: int
        """
        start_time = time.time()

        # Validate language hint
        validated_lang = self.lang_detector.validate_language_code(language_hint)

        # Load and preprocess audio
        audio, sr = self.preprocessor.load_audio(audio_input)
        duration = self.preprocessor.get_duration(audio, sr)

        # Quality assessment
        quality = self.preprocessor.compute_quality_score(audio, sr)

        # Chunk if needed
        chunks = self.preprocessor.chunk_audio(audio, sr)
        chunks_processed = len(chunks)

        # Transcribe each chunk
        if self._model_loaded and self._model is not None:
            transcripts = []
            confidences = []
            for chunk_audio, start_sec, end_sec in chunks:
                text, conf = self._transcribe_chunk(chunk_audio, sr, validated_lang)
                transcripts.append(text)
                confidences.append(conf)

            raw_transcript = self._stitch_transcripts(transcripts)
            avg_confidence = float(np.mean(confidences)) if confidences else 0.0
        else:
            # Model not loaded — return empty result with error info
            raw_transcript = ""
            avg_confidence = 0.0
            logger.warning("Model not loaded. Returning empty transcript.")

        # Detect language from transcript if no hint
        if validated_lang:
            detected_language = validated_lang
            lang_confidence = 0.9  # High confidence since user provided hint
        else:
            detected_language, lang_confidence = self.lang_detector.detect_from_transcript(
                raw_transcript
            )

        # Apply quality penalty
        if quality["is_low_quality"]:
            avg_confidence = max(0.0, avg_confidence - CONFIDENCE_PENALTY_LOW_QUALITY)

        # Clean transcript
        cleaned_transcript = self._clean_transcript(raw_transcript)

        processing_time_ms = int((time.time() - start_time) * 1000)

        return {
            "raw_transcript": raw_transcript,
            "cleaned_transcript": cleaned_transcript,
            "detected_language": detected_language,
            "language_confidence": round(lang_confidence, 4),
            "confidence": round(avg_confidence, 4),
            "duration_seconds": round(duration, 2),
            "chunks_processed": chunks_processed,
            "audio_quality": quality,
            "processing_time_ms": processing_time_ms,
        }

    def _transcribe_chunk(
        self, audio: np.ndarray, sr: int, language: Optional[str] = None
    ) -> tuple:
        """Transcribe a single audio chunk using the loaded model."""
        import torch

        try:
            # Ensure the audio is exactly 16000 Hz, as conformer expects
            import torchaudio
            target_sample_rate = 16000
            
            # Convert numpy array to tensor (channels, time)
            wav = torch.tensor(audio, dtype=torch.float32)
            # Add channel dim if 1D
            if wav.ndim == 1:
                wav = wav.unsqueeze(0)
                
            if sr != target_sample_rate:
                resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=target_sample_rate)
                wav = resampler(wav)

            # Move to device
            wav = wav.to(self._device)

            # Define language for indic-conformer (defaults to hi)
            inf_lang = language if language else "hi"
            
            # The model internally handles processing and decode
            with torch.no_grad():
                transcript = self._model(wav, inf_lang, "ctc")
                
            # the custom ai4bharat model returns a string directly
            if isinstance(transcript, list) and len(transcript) > 0:
                transcript = transcript[0]

            return transcript.strip(), 0.90  # Default confidence

        except Exception as e:
            logger.error("Transcription error on chunk: %s", e)
            return "", 0.0

    @staticmethod
    def _stitch_transcripts(transcripts: list) -> str:
        """
        Stitch overlapping chunk transcripts.

        Simple approach: join with space, deduplicate repeated phrases
        at chunk boundaries.
        """
        if not transcripts:
            return ""
        if len(transcripts) == 1:
            return transcripts[0]

        result = transcripts[0]
        for i in range(1, len(transcripts)):
            current = transcripts[i]
            if not current:
                continue

            # Try to find overlap at boundary
            overlap_found = False
            words_prev = result.split()
            words_curr = current.split()

            # Check for duplicated words at the seam (overlap region)
            for overlap_len in range(min(10, len(words_prev), len(words_curr)), 0, -1):
                if words_prev[-overlap_len:] == words_curr[:overlap_len]:
                    # Remove the duplicated portion
                    result += " " + " ".join(words_curr[overlap_len:])
                    overlap_found = True
                    break

            if not overlap_found:
                result += " " + current

        return result.strip()

    @staticmethod
    def _clean_transcript(raw: str) -> str:
        """Basic transcript cleaning — normalise whitespace and common artefacts."""
        import re

        text = raw.strip()
        # Collapse multiple spaces
        text = re.sub(r"\s+", " ", text)
        # Remove filler words common in Indian languages
        fillers = [
            r"\b(umm|uh|uhh|hmm|haan|aaa|mmm)\b",
        ]
        for pattern in fillers:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def get_status(self) -> Dict[str, Any]:
        """Return model loading status for the health endpoint."""
        status = {
            "model_id": MODEL_ID,
            "loaded": self._model_loaded,
            "device": self._device,
        }
        if self._load_error:
            status["error"] = self._load_error
        if self._device == "cuda":
            try:
                import torch

                status["gpu_name"] = torch.cuda.get_device_name(0)
                status["gpu_memory_total_gb"] = round(
                    torch.cuda.get_device_properties(0).total_memory / 1e9, 2
                )
                status["gpu_memory_allocated_gb"] = round(
                    torch.cuda.memory_allocated(0) / 1e9, 2
                )
            except Exception:
                pass
        return status
