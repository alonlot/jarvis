"""Text-to-speech. Local (pyttsx3) or remote (configurable URL/key/model)."""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

import requests

from ..core.config import Config

log = logging.getLogger(__name__)


class TTS:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._lock = threading.Lock()
        self._engine = None

    @property
    def enabled(self) -> bool:
        return bool(self.cfg.get("tts.enabled", False)) and self.cfg.get("tts.backend") != "none"

    def speak(self, text: str) -> None:
        if not self.enabled or not text.strip():
            return
        backend = self.cfg.get("tts.backend", "local")
        try:
            if backend == "local":
                self._speak_local(text)
            elif backend == "remote":
                self._speak_remote(text)
            else:
                log.warning("Unknown tts.backend: %s", backend)
        except Exception:
            log.exception("TTS failed")

    def speak_async(self, text: str) -> None:
        threading.Thread(target=self.speak, args=(text,), daemon=True).start()

    # ------------------------------------------------------------------
    def _ensure_local_engine(self):
        if self._engine is not None:
            return self._engine
        import pyttsx3
        eng = pyttsx3.init()
        rate = self.cfg.get("tts.local.rate")
        vol = self.cfg.get("tts.local.volume")
        hint = (self.cfg.get("tts.local.voice_hint") or "").lower()
        if rate:
            eng.setProperty("rate", int(rate))
        if vol is not None:
            eng.setProperty("volume", float(vol))
        if hint:
            for v in eng.getProperty("voices"):
                if hint in (v.name or "").lower() or hint in (v.id or "").lower():
                    eng.setProperty("voice", v.id)
                    break
        self._engine = eng
        return eng

    def _speak_local(self, text: str) -> None:
        with self._lock:
            eng = self._ensure_local_engine()
            eng.say(text)
            eng.runAndWait()

    # ------------------------------------------------------------------
    def _speak_remote(self, text: str) -> None:
        base = self.cfg.get("tts.remote.base_url")
        key = self.cfg.resolve_secret("tts.remote.api_key", "tts.remote.api_key_env")
        model = self.cfg.get("tts.remote.model")
        voice = self.cfg.get("tts.remote.voice")
        fmt = self.cfg.get("tts.remote.format", "mp3")

        payload = {"model": model, "input": text, "voice": voice, "format": fmt}
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        r = requests.post(base, json=payload, headers=headers, timeout=60)
        r.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=False) as f:
            f.write(r.content)
            path = Path(f.name)
        try:
            self._play_file(path)
        finally:
            path.unlink(missing_ok=True)

    @staticmethod
    def _play_file(path: Path) -> None:
        # Pick the first available player on PATH. Linux-friendly defaults.
        for player in ("paplay", "aplay", "ffplay", "mpv", "afplay"):
            if shutil.which(player):
                args = [player, str(path)]
                if player == "ffplay":
                    args = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)]
                subprocess.run(args, check=False)
                return
        log.warning("No audio player found on PATH (tried paplay/aplay/ffplay/mpv/afplay).")
