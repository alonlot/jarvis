"""Main Jarvis chat window."""
from __future__ import annotations

import threading
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QHBoxLayout, QLineEdit, QMainWindow, QMenu, QMenuBar, QPushButton,
    QStatusBar, QTextEdit, QToolBar, QVBoxLayout, QWidget,
)

from ..core.assistant import Assistant
from .routines_dialog import RoutinesDialog
from .settings_dialog import SettingsDialog


class ChatWorker(QThread):
    """Runs assistant.chat() off the UI thread."""
    finished_with_reply = pyqtSignal(str)

    def __init__(self, assistant: Assistant, text: str, pending_id: Optional[str] = None):
        super().__init__()
        self.assistant = assistant
        self.text = text
        self.pending_id = pending_id

    def run(self) -> None:
        try:
            if self.pending_id:
                reply = self.assistant.confirm_pending(self.pending_id, self.text)
            else:
                reply = self.assistant.chat(self.text)
        except Exception as e:                                 # noqa: BLE001
            reply = f"(error: {e})"
        # Reply also fires on_assistant_message which the GUI bridge handles —
        # we still emit here so the chat window can clear its busy state.
        self.finished_with_reply.emit(reply)


class ChatWindow(QMainWindow):
    def __init__(self, assistant: Assistant, voice):
        super().__init__()
        self.assistant = assistant
        self.voice = voice
        self._pending_id: Optional[str] = None
        self._worker: Optional[ChatWorker] = None

        self.setWindowTitle("Jarvis")
        self.resize(720, 720)

        self._build_ui()
        self._build_menu()

        # Greet.
        addr = assistant.config.get("persona.address_user_as", "sir")
        self.append_assistant(f"At your service, {addr}.")

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)

        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setFont(QFont("Sans", 10))
        layout.addWidget(self.transcript, 1)

        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Speak freely, sir.")
        self.input.returnPressed.connect(self._on_send)
        input_row.addWidget(self.input, 1)

        self.mic_btn = QPushButton("🎙")
        self.mic_btn.setToolTip("Push-to-talk")
        self.mic_btn.clicked.connect(self._on_mic)
        input_row.addWidget(self.mic_btn)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._on_send)
        input_row.addWidget(self.send_btn)

        layout.addLayout(input_row)
        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())

        # Push-to-talk hotkey.
        hotkey = self.assistant.config.get("voice_activation.push_to_talk.hotkey", "ctrl+space")
        QShortcut(QKeySequence(hotkey.replace("ctrl", "Ctrl").replace("+", "+")), self,
                  activated=self._on_mic)

    def _build_menu(self) -> None:
        mbar: QMenuBar = self.menuBar()

        file_menu: QMenu = mbar.addMenu("&Jarvis")
        act_settings = QAction("Settings…", self)
        act_settings.triggered.connect(self._open_settings)
        file_menu.addAction(act_settings)

        act_routines = QAction("Routines…", self)
        act_routines.triggered.connect(self._open_routines)
        file_menu.addAction(act_routines)

        file_menu.addSeparator()
        act_clear = QAction("Clear chat history", self)
        act_clear.triggered.connect(self._clear_history)
        file_menu.addAction(act_clear)

        file_menu.addSeparator()
        act_quit = QAction("Quit", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

    # ------------------------------------------------------------------
    def append_user(self, text: str) -> None:
        self.transcript.append(f"<p><b>You:</b> {self._html_escape(text)}</p>")

    def append_assistant(self, text: str) -> None:
        self.transcript.append(f"<p><b>Jarvis:</b> {self._html_escape(text)}</p>")

    @staticmethod
    def _html_escape(s: str) -> str:
        return (s.replace("&", "&amp;").replace("<", "&lt;")
                 .replace(">", "&gt;").replace("\n", "<br>"))

    # ------------------------------------------------------------------
    def _on_send(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.append_user(text)
        self._start_worker(text, self._pending_id)
        self._pending_id = None

    def on_voice_text(self, text: str) -> None:
        if not text:
            return
        self.append_user(text + "  (🎙)")
        self._start_worker(text, self._pending_id)
        self._pending_id = None

    def on_question_asked(self, pending_id: str, question: str) -> None:
        # Assistant has asked us something; next user message answers it.
        self._pending_id = pending_id
        self.statusBar().showMessage("Awaiting your reply…", 0)

    def _start_worker(self, text: str, pending_id: Optional[str]) -> None:
        self.send_btn.setEnabled(False)
        self.input.setEnabled(False)
        self.statusBar().showMessage("Thinking…", 0)
        self._worker = ChatWorker(self.assistant, text, pending_id)
        self._worker.finished_with_reply.connect(self._on_reply_ready)
        self._worker.start()

    def _on_reply_ready(self, _reply: str) -> None:
        # Actual rendering happens via on_assistant_message → bridge → append_assistant
        # so we just clear the busy state here.
        self.send_btn.setEnabled(True)
        self.input.setEnabled(True)
        self.input.setFocus()
        self.statusBar().clearMessage()

    def _on_mic(self) -> None:
        self.voice.request_listen()
        self.statusBar().showMessage("Listening…", 1500)

    # ------------------------------------------------------------------
    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.assistant, self)
        dlg.exec()

    def _open_routines(self) -> None:
        dlg = RoutinesDialog(self.assistant, self)
        dlg.exec()

    def _clear_history(self) -> None:
        self.assistant.memory.clear_turns()
        self.transcript.clear()
        self.append_assistant("History cleared, sir.")
