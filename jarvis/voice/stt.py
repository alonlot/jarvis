"""Speech-to-text. Local (faster-whisper) or remote (HTTP)."""
from __future__ import annotations

import logging
import tempfile
import wave
from pathlib import Path
from typing import Optional

import numpy as np
import requests

from ..core.config import Config

log = logging.getLogger(__name__)


class STT:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._whisper = None

    @property
    def enabled(self) -> bool:
        return bool(self.cfg.get("stt.enabled", False)) and self.cfg.get("stt.backend") != "none"

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        if not self.enabled:
            return ""
        backend = self.cfg.get("stt.backend", "local")
        if backend == "local":
            return self._transcribe_local(audio, sample_rate)
        if backend == "remote":
            return self._transcribe_remote(audio, sample_rate)
        log.warning("Unknown stt.backend: %s", backend)
        return ""

    # ------------------------------------------------------------------
    def _ensure_whisper(self):
        if self._whisper is not None:
            return self._whisper
        from faster_whisper import WhisperModel
        model_name = self.cfg.get("stt.local.model", "base.en")
        device = self.cfg.get("stt.local.device", "auto")
        compute = "int8" if device == "cpu" else "auto"
        self._whisper = WhisperModel(model_name, device=device, compute_type=compute)
        return self._whisper

    def _transcribe_local(self, audio: np.ndarray, sr: int) -> str:
        try:
            model = self._ensure_whisper()
        except ImportError:
            log.error("faster-whisper not installed. `pip install faster-whisper` "
                      "or switch stt.backend to remote.")
            return ""
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32) / (32768.0 if np.issubdtype(audio.dtype, np.integer) else 1.0)
        segments, _ = model.transcribe(audio, beam_size=1, language=None)
        return " ".join(s.text for s in segments).strip()

    # ------------------------------------------------------------------
    def _transcribe_remote(self, audio: np.ndarray, sr: int) -> str:
        base = self.cfg.get("stt.remote.base_url")
        key = self.cfg.resolve_secret("stt.remote.api_key", "stt.remote.api_key_env")
        model = self.cfg.get("stt.remote.model", "whisper-1")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = Path(f.name)
        try:
            _write_wav(path, audio, sr)
            with path.open("rb") as fh:
                files = {"file": (path.name, fh, "audio/wav")}
                data = {"model": model}
                headers = {"Authorization": f"Bearer {key}"} if key else {}
                r = requests.post(base, files=files, data=data, headers=headers, timeout=60)
            r.raise_for_status()
            return (r.json().get("text") or "").strip()
        finally:
            path.unlink(missing_ok=True)


def _write_wav(path: Path, audio: np.ndarray, sr: int) -> None:
    if audio.dtype != np.int16:
        audio = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(audio.tobytes())
