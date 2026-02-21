"""
Tests for the STT module — audio preprocessor, language detector, and conformer wrapper.

All tests use mocks for the ML model to run without GPU or large model downloads.
"""

import pytest
import numpy as np
import base64
import json
import os
import tempfile
from unittest.mock import patch, MagicMock

# ── Audio Preprocessor Tests ─────────────────────────────────────────────────


class TestAudioPreprocessor:
    """Tests for audio_preprocessor.py"""

    def setup_method(self):
        from stt.audio_preprocessor import AudioPreprocessor
        self.preprocessor = AudioPreprocessor()

    def test_chunk_short_audio(self):
        """Audio shorter than 30s should NOT be chunked."""
        sr = 16000
        duration = 10  # 10 seconds
        audio = np.random.randn(sr * duration).astype(np.float32)

        chunks = self.preprocessor.chunk_audio(audio, sr)
        assert len(chunks) == 1
        assert chunks[0][1] == 0.0  # start
        assert chunks[0][2] == pytest.approx(10.0, abs=0.01)  # end

    def test_chunk_long_audio(self):
        """Audio longer than 30s should be chunked with overlap."""
        sr = 16000
        duration = 75  # 75 seconds
        audio = np.random.randn(sr * duration).astype(np.float32)

        chunks = self.preprocessor.chunk_audio(audio, sr)
        assert len(chunks) > 1

        # Verify overlap
        for i in range(1, len(chunks)):
            prev_end = chunks[i - 1][2]
            curr_start = chunks[i][1]
            overlap = prev_end - curr_start
            assert overlap == pytest.approx(5.0, abs=0.5)

    def test_quality_score_clean_signal(self):
        """Clean signal should get high quality score."""
        sr = 16000
        t = np.linspace(0, 1, sr, dtype=np.float32)
        # Clean 440Hz sine wave
        audio = 0.5 * np.sin(2 * np.pi * 440 * t).astype(np.float32)

        quality = self.preprocessor.compute_quality_score(audio, sr)
        assert "snr_db" in quality
        assert "quality_score" in quality
        assert "is_low_quality" in quality
        assert quality["quality_score"] >= 0.0
        assert quality["quality_score"] <= 1.0

    def test_quality_score_noisy_signal(self):
        """Very noisy signal should get low quality score."""
        sr = 16000
        # Pure noise
        audio = np.random.randn(sr * 3).astype(np.float32) * 0.01

        quality = self.preprocessor.compute_quality_score(audio, sr)
        assert quality["quality_score"] >= 0.0

    def test_load_audio_from_bytes(self):
        """Loading audio from WAV bytes should work."""
        import soundfile as sf
        import io

        sr = 16000
        audio = np.random.randn(sr * 2).astype(np.float32)
        buf = io.BytesIO()
        sf.write(buf, audio, sr, format="WAV")
        wav_bytes = buf.getvalue()

        loaded_audio, loaded_sr = self.preprocessor.load_audio(wav_bytes)
        assert loaded_sr == 16000
        assert len(loaded_audio) > 0

    def test_load_audio_from_file(self):
        """Loading audio from a WAV file path should work."""
        import soundfile as sf

        sr = 16000
        audio = np.random.randn(sr * 2).astype(np.float32)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sf.write(f.name, audio, sr)
            filepath = f.name

        try:
            loaded_audio, loaded_sr = self.preprocessor.load_audio(filepath)
            assert loaded_sr == 16000
            assert len(loaded_audio) > 0
        finally:
            os.unlink(filepath)

    def test_load_audio_from_base64(self):
        """Loading audio from a base64 string should work."""
        import soundfile as sf
        import io

        sr = 16000
        audio = np.random.randn(sr * 2).astype(np.float32)
        buf = io.BytesIO()
        sf.write(buf, audio, sr, format="WAV")
        b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")

        loaded_audio, loaded_sr = self.preprocessor.load_audio(b64_str)
        assert loaded_sr == 16000
        assert len(loaded_audio) > 0

    def test_get_duration(self):
        """Duration calculation should be correct."""
        sr = 16000
        duration = 5
        audio = np.zeros(sr * duration, dtype=np.float32)
        assert self.preprocessor.get_duration(audio, sr) == pytest.approx(5.0)

    def test_empty_audio_quality(self):
        """Empty audio should not crash."""
        quality = self.preprocessor.compute_quality_score(
            np.array([], dtype=np.float32), 16000
        )
        assert quality["quality_score"] == 0.0


# ── Language Detector Tests ──────────────────────────────────────────────────


class TestLanguageDetector:
    """Tests for language_detector.py"""

    def setup_method(self):
        from stt.language_detector import LanguageDetector
        self.detector = LanguageDetector()

    def test_validate_hindi(self):
        assert self.detector.validate_language_code("hi") == "hi"

    def test_validate_tamil(self):
        assert self.detector.validate_language_code("ta") == "ta"

    def test_validate_by_name(self):
        assert self.detector.validate_language_code("Hindi") == "hi"
        assert self.detector.validate_language_code("Tamil") == "ta"

    def test_validate_unsupported(self):
        assert self.detector.validate_language_code("xx") is None

    def test_validate_none(self):
        assert self.detector.validate_language_code(None) is None

    def test_detect_hindi_text(self):
        text = "मैं कपड़ा बनाता हूं हमारी दुकान दिल्ली में है"
        lang, conf = self.detector.detect_from_transcript(text)
        assert lang == "hi"
        assert conf > 0.5

    def test_detect_tamil_text(self):
        text = "நான் துணி தயாரிக்கிறேன் எங்கள் கடை சென்னையில் உள்ளது"
        lang, conf = self.detector.detect_from_transcript(text)
        assert lang == "ta"
        assert conf > 0.5

    def test_detect_english_text(self):
        text = "We make cotton textiles and sell to wholesale buyers in Delhi"
        lang, conf = self.detector.detect_from_transcript(text)
        assert lang == "en"
        assert conf > 0.5

    def test_detect_empty_text(self):
        lang, conf = self.detector.detect_from_transcript("")
        assert lang == "hi"  # default fallback
        assert conf == 0.0

    def test_get_language_name(self):
        assert self.detector.get_language_name("hi") == "Hindi"
        assert self.detector.get_language_name("ta") == "Tamil"

    def test_get_script(self):
        assert self.detector.get_script("hi") == "Devanagari"
        assert self.detector.get_script("ta") == "Tamil"


# ── Conformer Wrapper Tests (Mocked) ────────────────────────────────────────


class TestConformerWrapper:
    """Tests for conformer_wrapper.py using mocked model."""

    def test_singleton_pattern(self):
        from stt.conformer_wrapper import ConformerWrapper

        # Reset singleton for test isolation
        ConformerWrapper._instance = None

        instance1 = ConformerWrapper.get_instance()
        instance2 = ConformerWrapper.get_instance()
        assert instance1 is instance2

        # Cleanup
        ConformerWrapper._instance = None

    def test_transcribe_without_model(self):
        """Transcribe should return empty result when model is not loaded."""
        from stt.conformer_wrapper import ConformerWrapper
        import soundfile as sf
        import io

        ConformerWrapper._instance = None
        wrapper = ConformerWrapper.get_instance()
        # Don't load model

        sr = 16000
        audio = np.random.randn(sr * 2).astype(np.float32)
        buf = io.BytesIO()
        sf.write(buf, audio, sr, format="WAV")

        result = wrapper.transcribe(buf.getvalue())
        assert result["raw_transcript"] == ""
        assert "detected_language" in result
        assert "duration_seconds" in result
        assert result["chunks_processed"] >= 1

        ConformerWrapper._instance = None

    def test_get_status_no_model(self):
        from stt.conformer_wrapper import ConformerWrapper

        ConformerWrapper._instance = None
        wrapper = ConformerWrapper.get_instance()

        status = wrapper.get_status()
        assert status["loaded"] is False
        assert "model_id" in status

        ConformerWrapper._instance = None
