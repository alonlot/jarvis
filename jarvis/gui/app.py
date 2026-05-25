"""GUI entry point. Wires the assistant to the chat window, overlay, and voice."""
from __future__ import annotations

import logging
import sys

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from ..core.assistant import Assistant
from ..voice.stt import STT
from ..voice.tts import TTS
from ..voice.wake_word import VoiceCapture
from .chat_window import ChatWindow
from .overlay import JarvisOverlay
from .styles import JARVIS_QSS

log = logging.getLogger(__name__)


class GuiBridge(QObject):
    """Cross-thread bridge — voice/TTS callbacks fire on worker threads;
    signals marshal them back onto the Qt main thread."""
    text_recognised = pyqtSignal(str)
    state_changed = pyqtSignal(str)
    assistant_said = pyqtSignal(str)
    question_asked = pyqtSignal(str, str)


def run_gui(assistant: Assistant) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Jarvis")
    app.setStyleSheet(JARVIS_QSS)
    app.setQuitOnLastWindowClosed(False)

    bridge = GuiBridge()

    # Voice setup.
    tts = TTS(assistant.config)
    stt = STT(assistant.config)
    voice = VoiceCapture(
        assistant.config, stt,
        on_text=lambda t: bridge.text_recognised.emit(t),
        on_state=lambda s: bridge.state_changed.emit(s),
    )
    assistant.voice = voice

    def _say(text: str) -> None:
        if not text:
            return
        bridge.assistant_said.emit(text)
        if tts.enabled:
            bridge.state_changed.emit("talking")

            def _after():
                bridge.state_changed.emit("idle")
            import threading

            def _speak_then_idle():
                tts.speak(text)
                _after()
            threading.Thread(target=_speak_then_idle, daemon=True).start()

    assistant.on_assistant_message.append(_say)
    assistant.on_question.append(lambda pid, q: bridge.question_asked.emit(pid, q))

    # Windows.
    overlay = JarvisOverlay(assistant.config)
    overlay.clicked.connect(voice.request_listen)

    chat = ChatWindow(assistant, voice)

    # State flows to BOTH the embedded reactor and the floating overlay.
    bridge.state_changed.connect(overlay.set_state)
    bridge.state_changed.connect(chat.set_state)

    bridge.text_recognised.connect(chat.on_voice_text)
    bridge.assistant_said.connect(chat.append_assistant)
    bridge.question_asked.connect(chat.on_question_asked)

    chat.show()
    if assistant.config.get("overlay.enabled", True):
        overlay.show()

    assistant.start_background_services()
    voice.start()

    rc = app.exec()
    voice.stop()
    assistant.shutdown()
    return rc
