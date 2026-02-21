"""
Audio Preprocessor — format conversion, chunking, and quality scoring.

Handles:
- Multi-format input (wav, mp3, m4a, base64 string, raw bytes)
- Resampling to 16kHz mono (required by IndicConformer)
- Chunking long audio (>30s) into overlapping 30s segments with 5s overlap
- SNR-based audio quality scoring
"""

import io
import os
import base64
import tempfile
import logging
from typing import List, Tuple, Optional, Union
from pathlib import Path

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
TARGET_SAMPLE_RATE = 16000
CHUNK_DURATION_SEC = 30.0
OVERLAP_DURATION_SEC = 5.0
LOW_QUALITY_SNR_THRESHOLD_DB = 15.0
CONFIDENCE_PENALTY_LOW_QUALITY = 0.15


class AudioPreprocessor:
    """Converts, resamples, chunks, and quality-scores audio for the STT pipeline."""

    def __init__(
        self,
        target_sr: int = TARGET_SAMPLE_RATE,
        chunk_duration: float = CHUNK_DURATION_SEC,
        overlap_duration: float = OVERLAP_DURATION_SEC,
    ):
        self.target_sr = target_sr
        self.chunk_duration = chunk_duration
        self.overlap_duration = overlap_duration

    # ── Public API ────────────────────────────────────────────────────────────

    def load_audio(
        self, audio_input: Union[str, bytes, Path]
    ) -> Tuple[np.ndarray, int]:
        """
        Load audio from any supported source.

        Args:
            audio_input: One of:
                - str file path (wav/mp3/m4a)
                - base64-encoded string
                - raw bytes

        Returns:
            Tuple of (audio_array, sample_rate) — 16 kHz mono float32 numpy array.
        """
        if isinstance(audio_input, (str, Path)):
            audio_input_str = str(audio_input)
            # Try to decode as base64 first (if it looks like one)
            if not os.path.exists(audio_input_str) and self._is_base64(audio_input_str):
                raw_bytes = base64.b64decode(audio_input_str)
                return self._load_from_bytes(raw_bytes)
            # Otherwise treat as file path
            return self._load_from_file(audio_input_str)
        elif isinstance(audio_input, bytes):
            return self._load_from_bytes(audio_input)
        else:
            raise ValueError(
                f"Unsupported audio_input type: {type(audio_input)}. "
                "Expected str (path or base64), bytes, or pathlib.Path."
            )

    def chunk_audio(
        self, audio: np.ndarray, sr: int
    ) -> List[Tuple[np.ndarray, float, float]]:
        """
        Split audio into overlapping chunks if longer than chunk_duration.

        Args:
            audio: 1-D float32 numpy array.
            sr: Sample rate.

        Returns:
            List of (chunk_array, start_sec, end_sec) tuples.
        """
        total_duration = len(audio) / sr
        if total_duration <= self.chunk_duration:
            return [(audio, 0.0, total_duration)]

        chunks: List[Tuple[np.ndarray, float, float]] = []
        chunk_samples = int(self.chunk_duration * sr)
        step_samples = int((self.chunk_duration - self.overlap_duration) * sr)

        start = 0
        while start < len(audio):
            end = min(start + chunk_samples, len(audio))
            chunk = audio[start:end]
            start_sec = start / sr
            end_sec = end / sr
            chunks.append((chunk, start_sec, end_sec))
            if end >= len(audio):
                break
            start += step_samples

        logger.info(
            "Chunked %.1fs audio into %d segments (%.0fs chunks, %.0fs overlap)",
            total_duration,
            len(chunks),
            self.chunk_duration,
            self.overlap_duration,
        )
        return chunks

    def compute_quality_score(self, audio: np.ndarray, sr: int) -> dict:
        """
        Estimate audio quality via simple SNR heuristic.

        Returns:
            dict with keys:
                - snr_db: estimated signal-to-noise ratio
                - quality_score: normalised 0–1 score
                - is_low_quality: True if SNR < threshold
        """
        snr_db = self._estimate_snr(audio)
        # Map SNR to a 0–1 score (0 dB → 0.0, 40 dB → 1.0)
        quality_score = float(np.clip(snr_db / 40.0, 0.0, 1.0))
        is_low_quality = snr_db < LOW_QUALITY_SNR_THRESHOLD_DB

        if is_low_quality:
            logger.warning(
                "Low audio quality detected: SNR=%.1f dB (threshold=%d dB). "
                "Confidence scores will be penalised by %.2f.",
                snr_db,
                LOW_QUALITY_SNR_THRESHOLD_DB,
                CONFIDENCE_PENALTY_LOW_QUALITY,
            )

        return {
            "snr_db": round(snr_db, 2),
            "quality_score": round(quality_score, 4),
            "is_low_quality": is_low_quality,
        }

    def get_duration(self, audio: np.ndarray, sr: int) -> float:
        """Return duration in seconds."""
        return len(audio) / sr

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load_from_file(self, filepath: str) -> Tuple[np.ndarray, int]:
        """Load from a file path, converting to 16 kHz mono."""
        try:
            audio, sr = sf.read(filepath, dtype="float32", always_2d=False)
        except Exception:
            # Fallback: try pydub for exotic formats (mp3, m4a, etc.)
            audio, sr = self._load_with_pydub(filepath)

        return self._normalise(audio, sr)

    def _load_from_bytes(self, raw_bytes: bytes) -> Tuple[np.ndarray, int]:
        """Load from raw bytes, converting to 16 kHz mono."""
        try:
            audio, sr = sf.read(io.BytesIO(raw_bytes), dtype="float32", always_2d=False)
        except Exception:
            # Write to temp file and use pydub
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(raw_bytes)
                tmp_path = f.name
            try:
                audio, sr = self._load_with_pydub(tmp_path)
            finally:
                os.unlink(tmp_path)

        return self._normalise(audio, sr)

    def _load_with_pydub(self, filepath: str) -> Tuple[np.ndarray, int]:
        """Use pydub as fallback for formats soundfile can't handle."""
        from pydub import AudioSegment

        seg = AudioSegment.from_file(filepath)
        seg = seg.set_channels(1).set_frame_rate(self.target_sr).set_sample_width(2)
        samples = np.array(seg.get_array_of_samples(), dtype=np.float32)
        samples /= 32768.0  # int16 → float32
        return samples, self.target_sr

    def _normalise(self, audio: np.ndarray, sr: int) -> Tuple[np.ndarray, int]:
        """Ensure mono float32 at target sample rate."""
        # Convert stereo → mono
        if audio.ndim == 2:
            audio = audio.mean(axis=1)

        # Resample if needed
        if sr != self.target_sr:
            try:
                import torchaudio
                import torch

                waveform = torch.from_numpy(audio).unsqueeze(0)
                resampler = torchaudio.transforms.Resample(
                    orig_freq=sr, new_freq=self.target_sr
                )
                waveform = resampler(waveform)
                audio = waveform.squeeze(0).numpy()
            except ImportError:
                # Fallback: scipy resample
                from scipy.signal import resample

                num_samples = int(len(audio) * self.target_sr / sr)
                audio = resample(audio, num_samples).astype(np.float32)
            sr = self.target_sr

        return audio.astype(np.float32), sr

    @staticmethod
    def _estimate_snr(audio: np.ndarray) -> float:
        """
        Rough SNR estimate using top-percentile energy vs bottom-percentile.

        This is a heuristic — not a proper VAD-based estimate, but sufficient
        for flagging noisy recordings.
        """
        if len(audio) == 0:
            return 0.0

        frame_length = 1024
        hop = 512
        energies = []
        for i in range(0, len(audio) - frame_length, hop):
            frame = audio[i : i + frame_length]
            energies.append(np.mean(frame ** 2))

        if not energies:
            return 0.0

        energies = np.array(energies)
        # Signal = top 80th percentile energy, noise = bottom 20th
        signal_energy = np.percentile(energies, 80)
        noise_energy = np.percentile(energies, 20)

        if noise_energy < 1e-10:
            return 40.0  # Very clean

        snr = 10 * np.log10(signal_energy / (noise_energy + 1e-10))
        return float(max(snr, 0.0))

    @staticmethod
    def _is_base64(s: str) -> bool:
        """Quick heuristic: does this look like a base64 string?"""
        if len(s) < 100:
            return False
        try:
            base64.b64decode(s[:64], validate=True)
            return True
        except Exception:
            return False
