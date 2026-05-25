"""Scrollable message-bubble chat view."""
from __future__ import annotations

import time

from PyQt6.QtCore import Qt, QTimer
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
        self.label.setMaximumWidth(560)
        layout.addWidget(self.label)


class _Row(QWidget):
    def __init__(self, bubble: _Bubble, role: str, meta: str = "", parent=None):
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


class ChatView(QScrollArea):
    """A vertically scrolling list of message bubbles."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._container = QWidget()
        self._container.setObjectName("chatContainer")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(24, 16, 24, 16)
        self._layout.setSpacing(4)
        self._layout.addStretch(1)
        self.setWidget(self._container)

    # ------------------------------------------------------------------
    def add_message(self, role: str, text: str, meta: str | None = None) -> None:
        bubble = _Bubble(text, role)
        if meta is None:
            meta = time.strftime("%H:%M")
            if role == "user":
                meta = f"you · {meta}"
            else:
                meta = f"jarvis · {meta}"
        row = _Row(bubble, role, meta=meta)
        # Insert before the trailing stretch.
        self._layout.insertWidget(self._layout.count() - 1, row)
        QTimer.singleShot(0, self._scroll_to_bottom)

    def add_user(self, text: str, voice: bool = False) -> None:
        self.add_message("user", text, meta=("you · 🎙 " + time.strftime("%H:%M")) if voice else None)

    def add_assistant(self, text: str) -> None:
        self.add_message("assistant", text)

    def add_system(self, text: str) -> None:
        # Render as a dimmed assistant bubble.
        self.add_message("assistant", text, meta=f"system · {time.strftime('%H:%M')}")

    def clear(self) -> None:
        # Remove everything except the trailing stretch.
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    # ------------------------------------------------------------------
    def _scroll_to_bottom(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())
