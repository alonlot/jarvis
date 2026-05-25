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

log = logging.getLogger(__name__)


class GuiBridge(QObject):
    """Cross-thread bridge — voice callbacks fire on the audio thread; signals
    marshal them back to the Qt main thread."""
    text_recognised = pyqtSignal(str)
    state_changed = pyqtSignal(str)
    assistant_said = pyqtSignal(str)
    question_asked = pyqtSignal(str, str)   # pending_id, question


def run_gui(assistant: Assistant) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Jarvis")
    app.setQuitOnLastWindowClosed(False)   # overlay can outlive chat window

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

    # Speak every assistant reply.
    assistant.on_assistant_message.append(lambda text: (
        bridge.assistant_said.emit(text),
        tts.speak_async(text),
    ))
    assistant.on_question.append(lambda pid, q: bridge.question_asked.emit(pid, q))

    # Windows.
    overlay = JarvisOverlay(assistant.config)
    overlay.clicked.connect(voice.request_listen)
    bridge.state_changed.connect(overlay.set_state)

    chat = ChatWindow(assistant, voice)
    bridge.text_recognised.connect(chat.on_voice_text)
    bridge.assistant_said.connect(chat.append_assistant)
    bridge.question_asked.connect(chat.on_question_asked)

    chat.show()
    if assistant.config.get("overlay.enabled", True):
        overlay.show()

    # Start scheduler + mic.
    assistant.start_background_services()
    voice.start()

    rc = app.exec()
    voice.stop()
    assistant.shutdown()
    return rc
