"""Main Jarvis window: sidebar nav + chat / routines / settings panels."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QPushButton, QStackedWidget, QStatusBar, QVBoxLayout, QWidget,
)

from ..core.assistant import Assistant
from .routines_panel import RoutinesPanel
from .settings_panel import SettingsPanel
from .widgets.arc_reactor import ArcReactorWidget
from .widgets.chat_view import ChatView


class ChatWorker(QThread):
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
        self.finished_with_reply.emit(reply)


# ---------------------------------------------------------------------------
class _Sidebar(QWidget):
    """Vertical nav rail."""

    nav_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(180)

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 16, 0, 16)
        v.setSpacing(2)

        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(18, 0, 18, 12)
        self.brand_reactor = ArcReactorWidget(self, size=28)
        brand_row.addWidget(self.brand_reactor)
        brand = QLabel("JARVIS")
        brand.setObjectName("brand")
        brand_row.addWidget(brand)
        brand_row.addStretch(1)
        v.addLayout(brand_row)

        self._buttons: list[QPushButton] = []
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        for i, label in enumerate(["Chat", "Routines", "Settings"]):
            btn = QPushButton(label)
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _=False, idx=i: self.nav_changed.emit(idx))
            self._group.addButton(btn, i)
            self._buttons.append(btn)
            v.addWidget(btn)

        v.addStretch(1)

        footer = QLabel("at your service, sir.")
        footer.setStyleSheet("color: #484f58; padding: 12px 18px; font-size: 9pt;")
        v.addWidget(footer)

    def select(self, index: int) -> None:
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)


# ---------------------------------------------------------------------------
class _ChatPanel(QWidget):
    """The chat view itself: big reactor at top + bubble chat + input bar."""

    send_requested = pyqtSignal(str)
    mic_requested = pyqtSignal()

    def __init__(self, assistant: Assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # ── Header with the embedded reactor + state label ────────────
        header = QWidget()
        header.setObjectName("headerArea")
        hv = QVBoxLayout(header)
        hv.setContentsMargins(0, 22, 0, 14)
        hv.setSpacing(8)
        hv.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.reactor = ArcReactorWidget(self, size=120, clickable=True)
        self.reactor.clicked.connect(self.mic_requested.emit)
        hv.addWidget(self.reactor, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.state_label = QLabel("READY, SIR.")
        self.state_label.setObjectName("stateLabel")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        hv.addWidget(self.state_label)
        v.addWidget(header)

        # ── Divider ───────────────────────────────────────────────────
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #21262d; background: #21262d; max-height: 1px;")
        v.addWidget(line)

        # ── Bubble chat ───────────────────────────────────────────────
        address = assistant.config.get("persona.address_user_as", "sir")
        self.chat = ChatView(address=address)
        v.addWidget(self.chat, 1)

        # ── Input bar ─────────────────────────────────────────────────
        bar = QWidget()
        bar.setStyleSheet("background: #010409; border-top: 1px solid #21262d;")
        bh = QHBoxLayout(bar)
        bh.setContentsMargins(16, 12, 16, 12)
        bh.setSpacing(10)

        self.input = QLineEdit()
        self.input.setObjectName("chatInput")
        self.input.setPlaceholderText("Speak freely, sir.")
        self.input.returnPressed.connect(self._emit_send)
        bh.addWidget(self.input, 1)

        self.mic_btn = QPushButton("🎙")
        self.mic_btn.setObjectName("micBtn")
        self.mic_btn.setToolTip("Push-to-talk")
        self.mic_btn.clicked.connect(self.mic_requested.emit)
        bh.addWidget(self.mic_btn)

        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("primary")
        self.send_btn.clicked.connect(self._emit_send)
        bh.addWidget(self.send_btn)
        v.addWidget(bar)

    # ------------------------------------------------------------------
    def _emit_send(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.send_requested.emit(text)

    def set_busy(self, busy: bool) -> None:
        self.send_btn.setEnabled(not busy)
        self.input.setEnabled(not busy)
        if not busy:
            self.input.setFocus()

    def set_state(self, state: str) -> None:
        self.reactor.set_state(state)
        self.state_label.setText(self.reactor.state_label().upper())


# ---------------------------------------------------------------------------
class ChatWindow(QMainWindow):
    def __init__(self, assistant: Assistant, voice):
        super().__init__()
        self.assistant = assistant
        self.voice = voice
        self._pending_id: Optional[str] = None
        self._worker: Optional[ChatWorker] = None

        self.setWindowTitle("Jarvis")
        self.resize(960, 740)
        self.setMinimumSize(700, 560)

        # Central layout: sidebar + stacked content.
        central = QWidget()
        central.setObjectName("mainCentral")
        h = QHBoxLayout(central)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        self.sidebar = _Sidebar()
        h.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.chat_panel = _ChatPanel(assistant)
        self.routines_panel = RoutinesPanel(assistant)
        self.settings_panel = SettingsPanel(assistant)
        self.stack.addWidget(self.chat_panel)      # 0
        self.stack.addWidget(self.routines_panel)  # 1
        self.stack.addWidget(self.settings_panel)  # 2
        h.addWidget(self.stack, 1)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())

        # Signals.
        self.sidebar.nav_changed.connect(self.stack.setCurrentIndex)
        self.chat_panel.send_requested.connect(self._on_send)
        self.chat_panel.mic_requested.connect(self._on_mic)

        # Default to chat.
        self.sidebar.select(0)
        self.stack.setCurrentIndex(0)

        # Push-to-talk hotkey (active anywhere in the window).
        hotkey = self.assistant.config.get("voice_activation.push_to_talk.hotkey", "ctrl+space")
        QShortcut(QKeySequence(hotkey), self, activated=self._on_mic)

        # Menu (kept for keyboard users).
        self._build_menu()

        # Don't render an opening greeting — the empty state already says
        # "At your service, {addr}.". A greeting bubble on top of that
        # would be a double-up.

    # ------------------------------------------------------------------
    def _build_menu(self) -> None:
        mbar = self.menuBar()
        m = mbar.addMenu("&Jarvis")

        for label, idx in [("Chat", 0), ("Routines", 1), ("Settings", 2)]:
            a = QAction(label, self)
            a.triggered.connect(lambda _=False, i=idx: (self.sidebar.select(i), self.stack.setCurrentIndex(i)))
            m.addAction(a)

        m.addSeparator()
        clr = QAction("Clear chat history", self)
        clr.triggered.connect(self._clear_history)
        m.addAction(clr)

        m.addSeparator()
        q = QAction("Quit", self)
        q.setShortcut(QKeySequence.StandardKey.Quit)
        q.triggered.connect(self.close)
        m.addAction(q)

    # ------------------------------------------------------------------
    # External-facing methods (called from app.py via signal bridge)
    # ------------------------------------------------------------------
    def append_assistant(self, text: str) -> None:
        self.chat_panel.chat.add_assistant(text)

    def on_voice_text(self, text: str) -> None:
        if not text:
            return
        self.chat_panel.chat.add_user(text, voice=True)
        # Jump to chat panel if user is mid-config.
        self.sidebar.select(0)
        self.stack.setCurrentIndex(0)
        self._start_worker(text, self._pending_id)
        self._pending_id = None

    def on_question_asked(self, pending_id: str, _question: str) -> None:
        self._pending_id = pending_id
        self.statusBar().showMessage("Awaiting your reply…", 0)

    def set_state(self, state: str) -> None:
        """Wired from the app.py bridge so the embedded reactor stays in sync."""
        self.chat_panel.set_state(state)

    # ------------------------------------------------------------------
    def _on_send(self, text: str) -> None:
        self.chat_panel.chat.add_user(text)
        self.sidebar.select(0)
        self.stack.setCurrentIndex(0)
        self._start_worker(text, self._pending_id)
        self._pending_id = None

    def _on_mic(self) -> None:
        self.voice.request_listen()
        self.statusBar().showMessage("Listening…", 1500)

    def _start_worker(self, text: str, pending_id: Optional[str]) -> None:
        self.chat_panel.set_busy(True)
        self.chat_panel.chat.show_typing()
        self.statusBar().showMessage("Thinking…", 0)
        self._worker = ChatWorker(self.assistant, text, pending_id)
        self._worker.finished_with_reply.connect(self._on_reply_ready)
        self._worker.start()

    def _on_reply_ready(self, _reply: str) -> None:
        self.chat_panel.chat.hide_typing()
        self.chat_panel.set_busy(False)
        self.statusBar().clearMessage()

    def _clear_history(self) -> None:
        self.assistant.memory.clear_turns()
        self.chat_panel.chat.clear()
        self.statusBar().showMessage("History cleared.", 2000)
