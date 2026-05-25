"""Wake-word + voice-capture pipeline.

Modes (from config.voice_activation.mode):
  - wake_word     — always-on listening; only acts after detecting wake phrase.
  - push_to_talk  — button (overlay click or hotkey) starts listening.
  - off           — no voice input.

After activation we capture until N seconds of silence, then transcribe.
The captured audio goes to STT, the resulting text goes to the chat callback.

openWakeWord is optional — if missing, the wake_word mode logs a warning and
falls back to push_to_talk semantics.
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Callable, Optional

import numpy as np

from ..core.config import Config
from .stt import STT

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHUNK_MS = 80
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_MS / 1000)

# Below this RMS the chunk is "silence" for VAD purposes.
SILENCE_RMS = 0.01


class VoiceCapture:
    """Microphone listener. Emits transcribed text via on_text callback."""

    def __init__(self, cfg: Config, stt: STT,
                 on_text: Callable[[str], None],
                 on_state: Optional[Callable[[str], None]] = None):
        self.cfg = cfg
        self.stt = stt
        self.on_text = on_text
        self.on_state = on_state or (lambda _s: None)

        self._stop = threading.Event()
        self._listen_requested = threading.Event()  # for push-to-talk
        self._thread: Optional[threading.Thread] = None
        self._oww = None

    # ------------------------------------------------------------------
    def start(self) -> None:
        mode = self.cfg.get("voice_activation.mode", "push_to_talk")
        if mode == "off":
            log.info("voice_activation.mode = off; not starting mic.")
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="voice-capture", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def request_listen(self) -> None:
        """Trigger immediate listening (push-to-talk / overlay click)."""
        self._listen_requested.set()

    # ------------------------------------------------------------------
    def _run(self) -> None:
        try:
            import sounddevice as sd
        except Exception:
            log.exception("sounddevice unavailable; voice disabled.")
            return

        mode = self.cfg.get("voice_activation.mode", "push_to_talk")
        if mode == "wake_word":
            self._init_wake_word()

        q: queue.Queue[np.ndarray] = queue.Queue()

        def callback(indata, frames, time_info, status):
            if status:
                log.debug("audio status: %s", status)
            q.put(indata[:, 0].copy())

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, blocksize=CHUNK_SAMPLES,
                            dtype="float32", callback=callback):
            log.info("Mic open (mode=%s).", mode)
            while not self._stop.is_set():
                try:
                    chunk = q.get(timeout=0.5)
                except queue.Empty:
                    continue

                triggered = False
                if mode == "wake_word":
                    triggered = self._wake_word_detected(chunk)
                if self._listen_requested.is_set():
                    self._listen_requested.clear()
                    triggered = True

                if triggered:
                    self.on_state("listening")
                    audio = self._capture_until_silence(q, primer=chunk)
                    self.on_state("processing")
                    text = self.stt.transcribe(audio, SAMPLE_RATE)
                    if text:
                        self.on_text(text)
                    self.on_state("idle")

    # ------------------------------------------------------------------
    def _init_wake_word(self) -> None:
        try:
            from openwakeword.model import Model
            model_name = self.cfg.get("voice_activation.wake_word.model", "hey_jarvis")
            self._oww = Model(wakeword_models=[model_name])
            log.info("openWakeWord loaded: %s", model_name)
        except Exception:
            log.warning("openWakeWord unavailable; wake-word mode degrades to push-to-talk.")
            self._oww = None

    def _wake_word_detected(self, chunk: np.ndarray) -> bool:
        if self._oww is None:
            return False
        # openWakeWord expects int16 samples.
        pcm = np.clip(chunk * 32767, -32768, 32767).astype(np.int16)
        scores = self._oww.predict(pcm)
        threshold = float(self.cfg.get("voice_activation.wake_word.threshold", 0.5))
        for name, score in scores.items():
            if score >= threshold:
                log.info("Wake word '%s' triggered (%.2f)", name, score)
                return True
        return False

    def _capture_until_silence(self, q: queue.Queue, primer: np.ndarray) -> np.ndarray:
        timeout = float(self.cfg.get(
            f"voice_activation.{self.cfg.get('voice_activation.mode', 'push_to_talk')}"
            f".silence_timeout_seconds", 10))
        chunks = [primer]
        last_voice = time.time()
        deadline = time.time() + 30  # hard cap
        while time.time() < deadline:
            try:
                c = q.get(timeout=0.3)
            except queue.Empty:
                continue
            chunks.append(c)
            rms = float(np.sqrt(np.mean(c * c) + 1e-12))
            if rms >= SILENCE_RMS:
                last_voice = time.time()
            elif time.time() - last_voice >= timeout:
                break
        return np.concatenate(chunks)
