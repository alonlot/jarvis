"""Main Jarvis window — Stark Industries HUD edition.

Top status bar (live system telemetry), left tactical sidebar (numbered
modules), main viewport (chat panel with embedded reactor + telemetry
labels + bracket-framed message blocks)."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
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
from .widgets.hud import CornerHudOverlay, HudStatusBar


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
    """Tactical left rail with numbered nav modules."""

    nav_changed = pyqtSignal(int)

    NAV_ITEMS = [
        ("01", "CHAT",     "// COMMS"),
        ("02", "ROUTINES", "// CRON"),
        ("03", "SETTINGS", "// CONFIG"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 18, 0, 18)
        v.setSpacing(0)

        # ── Brand block ──────────────────────────────────────────────
        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(18, 0, 18, 6)
        brand_row.setSpacing(10)
        self.brand_reactor = ArcReactorWidget(self, size=34)
        brand_row.addWidget(self.brand_reactor)
        brand_box = QVBoxLayout()
        brand_box.setSpacing(0)
        brand = QLabel("JARVIS")
        brand.setObjectName("brand")
        brand_sub = QLabel("STARK INDUSTRIES")
        brand_sub.setObjectName("brandSub")
        brand_box.addWidget(brand)
        brand_box.addWidget(brand_sub)
        brand_row.addLayout(brand_box)
        brand_row.addStretch(1)
        v.addLayout(brand_row)

        # Divider.
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background: #0a3a5a; max-height: 1px; margin: 14px 18px;")
        v.addWidget(line)

        v.addSpacing(4)

        # ── Section header ───────────────────────────────────────────
        sec = QLabel("◢ MODULES")
        sec.setObjectName("navCode")
        v.addWidget(sec)
        v.addSpacing(6)

        # ── Nav items ────────────────────────────────────────────────
        self._buttons: list[QPushButton] = []
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for i, (code, label, sub) in enumerate(self.NAV_ITEMS):
            btn = QPushButton(f"  {code}   {label}")
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.setToolTip(sub)
            btn.clicked.connect(lambda _=False, idx=i: self.nav_changed.emit(idx))
            self._group.addButton(btn, i)
            self._buttons.append(btn)
            v.addWidget(btn)

        v.addStretch(1)

        # ── Footer block ─────────────────────────────────────────────
        footer = QLabel("◢ AT YOUR SERVICE, SIR.")
        footer.setStyleSheet(
            "color: #5a8fa8; padding: 12px 20px; font-size: 8pt; letter-spacing: 3px;"
        )
        v.addWidget(footer)

    def select(self, index: int) -> None:
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)


# ---------------------------------------------------------------------------
class _ChatPanel(QWidget):
    send_requested = pyqtSignal(str)
    mic_requested = pyqtSignal()

    def __init__(self, assistant: Assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # ── Header: reactor + telemetry triad ─────────────────────────
        header = QWidget()
        header.setObjectName("headerArea")
        hv = QVBoxLayout(header)
        hv.setContentsMargins(0, 24, 0, 18)
        hv.setSpacing(6)

        # Telemetry row above reactor.
        tele = QHBoxLayout()
        tele.setContentsMargins(0, 0, 0, 0)
        self.tele_left = QLabel("◢ VOX_LINK // STANDBY")
        self.tele_left.setObjectName("telemetry")
        self.tele_left.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.tele_right = QLabel("MODE: PTT  //  CH: 01 ◤")
        self.tele_right.setObjectName("telemetry")
        self.tele_right.setAlignment(Qt.AlignmentFlag.AlignRight)
        tele.addWidget(self.tele_left, 1)
        tele.addWidget(self.tele_right, 1)
        hv.addLayout(tele)

        hv.addSpacing(4)

        # Reactor centered.
        reactor_row = QHBoxLayout()
        reactor_row.addStretch(1)
        self.reactor = ArcReactorWidget(self, size=150, clickable=True)
        self.reactor.clicked.connect(self.mic_requested.emit)
        reactor_row.addWidget(self.reactor)
        reactor_row.addStretch(1)
        hv.addLayout(reactor_row)

        hv.addSpacing(2)

        # State caption + sub-caption.
        self.state_label = QLabel("READY")
        self.state_label.setObjectName("stateLabel")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        hv.addWidget(self.state_label)

        self.state_sub = QLabel("◢  AT YOUR SERVICE, SIR  ◤")
        self.state_sub.setObjectName("stateSub")
        self.state_sub.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        hv.addWidget(self.state_sub)

        v.addWidget(header)

        # ── Bubble chat ───────────────────────────────────────────────
        self.chat = ChatView()
        v.addWidget(self.chat, 1)

        # ── Input bar ─────────────────────────────────────────────────
        bar = QWidget()
        bar.setObjectName("inputBar")
        bh = QHBoxLayout(bar)
        bh.setContentsMargins(20, 14, 20, 14)
        bh.setSpacing(10)

        prompt = QLabel("▶")
        prompt.setStyleSheet("color: #00d4ff; font-size: 12pt;")
        bh.addWidget(prompt)

        self.input = QLineEdit()
        self.input.setObjectName("chatInput")
        self.input.setPlaceholderText("ENTER COMMAND...")
        self.input.returnPressed.connect(self._emit_send)
        bh.addWidget(self.input, 1)

        self.mic_btn = QPushButton("◉")
        self.mic_btn.setObjectName("micBtn")
        self.mic_btn.setToolTip("Push-to-talk")
        self.mic_btn.clicked.connect(self.mic_requested.emit)
        bh.addWidget(self.mic_btn)

        self.send_btn = QPushButton("TRANSMIT")
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
        self.state_label.setText(self.reactor.state_label())
        sub_map = {
            "idle":       "◢  AT YOUR SERVICE, SIR  ◤",
            "listening":  "◢  AUDIO STREAM ACTIVE  ◤",
            "processing": "◢  COMPUTING RESPONSE  ◤",
            "talking":    "◢  TRANSMITTING AUDIO  ◤",
        }
        self.state_sub.setText(sub_map.get(state, ""))
        # Telemetry left mirrors the state.
        tele_map = {
            "idle":       "◢ VOX_LINK // STANDBY",
            "listening":  "◢ VOX_LINK // RX ACTIVE",
            "processing": "◢ COMPUTE // RUNNING",
            "talking":    "◢ VOX_LINK // TX ACTIVE",
        }
        self.tele_left.setText(tele_map.get(state, "◢ VOX_LINK // STANDBY"))


# ---------------------------------------------------------------------------
class ChatWindow(QMainWindow):
    def __init__(self, assistant: Assistant, voice):
        super().__init__()
        self.assistant = assistant
        self.voice = voice
        self._pending_id: Optional[str] = None
        self._worker: Optional[ChatWorker] = None

        self.setWindowTitle("J.A.R.V.I.S")
        self.resize(1040, 780)
        self.setMinimumSize(820, 600)

        # ── Top-level layout: HUD bar / (sidebar + stacked content) ──
        central = QWidget()
        central.setObjectName("mainCentral")
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.hud = HudStatusBar(assistant)
        outer.addWidget(self.hud)

        body = QWidget()
        body.setObjectName("mainCentral")
        h = QHBoxLayout(body)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        self.sidebar = _Sidebar()
        h.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.chat_panel = _ChatPanel(assistant)
        self.routines_panel = RoutinesPanel(assistant)
        self.settings_panel = SettingsPanel(assistant)
        self.stack.addWidget(self.chat_panel)
        self.stack.addWidget(self.routines_panel)
        self.stack.addWidget(self.settings_panel)
        h.addWidget(self.stack, 1)

        outer.addWidget(body, 1)
        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())

        # Decorative outer corner brackets.
        self._hud_overlay = CornerHudOverlay(central)

        # Signals.
        self.sidebar.nav_changed.connect(self.stack.setCurrentIndex)
        self.chat_panel.send_requested.connect(self._on_send)
        self.chat_panel.mic_requested.connect(self._on_mic)

        # Default to chat.
        self.sidebar.select(0)
        self.stack.setCurrentIndex(0)

        hotkey = self.assistant.config.get("voice_activation.push_to_talk.hotkey", "ctrl+space")
        QShortcut(QKeySequence(hotkey), self, activated=self._on_mic)

        self._build_menu()

        addr = assistant.config.get("persona.address_user_as", "sir")
        self.chat_panel.chat.add_assistant(f"At your service, {addr}.")
        self.statusBar().showMessage("SYSTEMS NOMINAL")

    # ------------------------------------------------------------------
    def _build_menu(self) -> None:
        mbar = self.menuBar()
        m = mbar.addMenu("&J.A.R.V.I.S")
        for label, idx in [("CHAT", 0), ("ROUTINES", 1), ("SETTINGS", 2)]:
            a = QAction(label, self)
            a.triggered.connect(lambda _=False, i=idx: (self.sidebar.select(i), self.stack.setCurrentIndex(i)))
            m.addAction(a)
        m.addSeparator()
        clr = QAction("CLEAR HISTORY", self)
        clr.triggered.connect(self._clear_history)
        m.addAction(clr)
        m.addSeparator()
        q = QAction("DISENGAGE", self)
        q.setShortcut(QKeySequence.StandardKey.Quit)
        q.triggered.connect(self.close)
        m.addAction(q)

    # ------------------------------------------------------------------
    def append_assistant(self, text: str) -> None:
        self.chat_panel.chat.add_assistant(text)

    def on_voice_text(self, text: str) -> None:
        if not text:
            return
        self.chat_panel.chat.add_user(text, voice=True)
        self.sidebar.select(0)
        self.stack.setCurrentIndex(0)
        self._start_worker(text, self._pending_id)
        self._pending_id = None

    def on_question_asked(self, pending_id: str, _question: str) -> None:
        self._pending_id = pending_id
        self.statusBar().showMessage("AWAITING REPLY...", 0)
        self.hud.set_status("AWAITING USER", "warn")

    def set_state(self, state: str) -> None:
        self.chat_panel.set_state(state)
        sev = "ok"
        hud_text = {
            "idle":       "SYSTEM ONLINE",
            "listening":  "RECEIVING AUDIO",
            "processing": "PROCESSING",
            "talking":    "TRANSMITTING",
        }.get(state, "SYSTEM ONLINE")
        if state == "processing":
            sev = "warn"
        self.hud.set_status(hud_text, sev)

    # ------------------------------------------------------------------
    def _on_send(self, text: str) -> None:
        self.chat_panel.chat.add_user(text)
        self.sidebar.select(0)
        self.stack.setCurrentIndex(0)
        self._start_worker(text, self._pending_id)
        self._pending_id = None

    def _on_mic(self) -> None:
        self.voice.request_listen()
        self.statusBar().showMessage("LISTENING...", 1500)

    def _start_worker(self, text: str, pending_id: Optional[str]) -> None:
        self.chat_panel.set_busy(True)
        self.statusBar().showMessage("COMPUTING...", 0)
        self.hud.set_status("PROCESSING", "warn")
        self._worker = ChatWorker(self.assistant, text, pending_id)
        self._worker.finished_with_reply.connect(self._on_reply_ready)
        self._worker.start()

    def _on_reply_ready(self, _reply: str) -> None:
        self.chat_panel.set_busy(False)
        self.statusBar().clearMessage()
        self.hud.set_status("SYSTEM ONLINE", "ok")

    def _clear_history(self) -> None:
        self.assistant.memory.clear_turns()
        self.chat_panel.chat.clear()
        self.chat_panel.chat.add_assistant("History cleared, sir.")
