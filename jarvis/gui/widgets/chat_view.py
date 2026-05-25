"""Scrollable message-bubble chat view with typing indicator and empty state."""
from __future__ import annotations

import math
import time

from PyQt6.QtCore import QPointF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPainter
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)


class _Bubble(QFrame):
    def __init__(self, text: str, role: str, parent=None):
        super().__init__(parent)
        self.setObjectName("bubbleUser" if role == "user" else "bubbleAssistant")
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(text)
        self.label.setObjectName("bubbleText")
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.label.setMaximumWidth(580)
        layout.addWidget(self.label)


class _Row(QWidget):
    def __init__(self, bubble: QWidget, role: str, meta: str = "", parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 4, 0, 4)
        outer.setSpacing(2)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        if role == "user":
            row.addStretch(1)
            row.addWidget(bubble, 0, Qt.AlignmentFlag.AlignRight)
        else:
            row.addWidget(bubble, 0, Qt.AlignmentFlag.AlignLeft)
            row.addStretch(1)
        outer.addLayout(row)

        if meta:
            meta_lbl = QLabel(meta)
            meta_lbl.setObjectName("bubbleMeta")
            outer.addWidget(meta_lbl,
                            alignment=Qt.AlignmentFlag.AlignRight if role == "user"
                            else Qt.AlignmentFlag.AlignLeft)


class _TypingDots(QFrame):
    """A small assistant-shaped bubble with three pulsing dots.
    Lives in the chat scroll while a reply is being computed."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("bubbleAssistant")
        self.setFixedSize(64, 30)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(60)

    def _tick(self) -> None:
        self._phase = (self._phase + 0.18) % (2 * math.pi)
        self.update()

    def paintEvent(self, _e) -> None:
        super().paintEvent(_e)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cy = self.height() / 2
        spacing = 12
        center_x = self.width() / 2
        for i, dx in enumerate((-spacing, 0, spacing)):
            offset = i * 0.6
            alpha = 0.35 + 0.55 * (math.sin(self._phase + offset) * 0.5 + 0.5)
            c = QColor("#8b949e"); c.setAlphaF(alpha)
            p.setBrush(QBrush(c))
            p.setPen(Qt.PenStyle.NoPen)
            r = 3.5
            p.drawEllipse(QPointF(center_x + dx, cy), r, r)


class _EmptyState(QWidget):
    """Shown when there are no messages — a quiet hint, no decoration."""

    def __init__(self, address: str = "sir", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 80, 40, 40)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        title = QLabel(f"At your service, {address}.")
        title.setObjectName("emptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)

        hint = QLabel(
            "Try a few:    "
            "“what's on my schedule today?”     "
            "“list my open merge requests”     "
            "“remember that my standup is at 9:45”"
        )
        hint.setObjectName("emptyHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)


class ChatView(QScrollArea):
    """Vertically scrolling list of message bubbles with typing indicator."""

    def __init__(self, address: str = "sir", parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._container = QWidget()
        self._container.setObjectName("chatContainer")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(28, 20, 28, 16)
        self._layout.setSpacing(6)

        self._empty = _EmptyState(address)
        self._layout.addWidget(self._empty)
        self._layout.addStretch(1)
        self.setWidget(self._container)

        self._typing_row: _Row | None = None
        self._has_messages = False

    # ------------------------------------------------------------------
    def _ensure_empty_hidden(self) -> None:
        if not self._has_messages:
            self._empty.hide()
            self._has_messages = True

    def _insert_above_stretch(self, w: QWidget) -> None:
        # Stretch is always the last item.
        self._layout.insertWidget(self._layout.count() - 1, w)

    def add_message(self, role: str, text: str, meta: str | None = None) -> None:
        self._ensure_empty_hidden()
        bubble = _Bubble(text, role)
        if meta is None:
            ts = time.strftime("%H:%M")
            meta = f"you · {ts}" if role == "user" else f"jarvis · {ts}"
        row = _Row(bubble, role, meta=meta)
        # Insert before any active typing indicator, otherwise above stretch.
        if self._typing_row is not None:
            idx = self._layout.indexOf(self._typing_row)
            self._layout.insertWidget(idx, row)
        else:
            self._insert_above_stretch(row)
        QTimer.singleShot(0, self._scroll_to_bottom)

    def add_user(self, text: str, voice: bool = False) -> None:
        meta = ("you · 🎙 " + time.strftime("%H:%M")) if voice else None
        self.add_message("user", text, meta=meta)

    def add_assistant(self, text: str) -> None:
        self.add_message("assistant", text)

    def add_system(self, text: str) -> None:
        self.add_message("assistant", text, meta=f"system · {time.strftime('%H:%M')}")

    # ------------------------------------------------------------------
    def show_typing(self) -> None:
        if self._typing_row is not None:
            return
        self._ensure_empty_hidden()
        dots = _TypingDots()
        row = _Row(dots, role="assistant", meta="")
        self._typing_row = row
        self._insert_above_stretch(row)
        QTimer.singleShot(0, self._scroll_to_bottom)

    def hide_typing(self) -> None:
        if self._typing_row is None:
            return
        row = self._typing_row
        self._typing_row = None
        row.setParent(None)
        row.deleteLater()

    # ------------------------------------------------------------------
    def clear(self) -> None:
        self.hide_typing()
        while self._layout.count() > 0:
            item = self._layout.takeAt(0)
            w = item.widget()
            if w and w is not self._empty:
                w.deleteLater()
        # Re-add the empty state and stretch.
        self._layout.addWidget(self._empty)
        self._empty.show()
        self._layout.addStretch(1)
        self._has_messages = False

    def _scroll_to_bottom(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())
