"""HUD-style chat view — bracketed message blocks with role tags."""
from __future__ import annotations

import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from .hud import BracketFrame


class _MessageBlock(QWidget):
    """One message: role label + bracketed text frame + timestamp line."""

    def __init__(self, text: str, role: str, meta: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(2)

        # Role label (above the frame).
        role_label = QLabel("// USER" if role == "user" else "// JARVIS")
        role_label.setObjectName("roleLabelUser" if role == "user" else "roleLabel")
        layout.addWidget(role_label, alignment=Qt.AlignmentFlag.AlignRight if role == "user"
                         else Qt.AlignmentFlag.AlignLeft)

        # Message text inside a bracketed frame.
        msg = QLabel(text)
        msg.setObjectName("bubbleText")
        msg.setWordWrap(True)
        msg.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        msg.setMaximumWidth(640)
        msg.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        bracketed = BracketFrame(msg, role=role)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        if role == "user":
            row.addStretch(1)
            row.addWidget(bracketed, 0, Qt.AlignmentFlag.AlignRight)
        else:
            row.addWidget(bracketed, 0, Qt.AlignmentFlag.AlignLeft)
            row.addStretch(1)
        layout.addLayout(row)

        # Meta line (timestamp / channel).
        if meta:
            ml = QLabel(meta)
            ml.setObjectName("bubbleMeta")
            layout.addWidget(ml, alignment=Qt.AlignmentFlag.AlignRight if role == "user"
                             else Qt.AlignmentFlag.AlignLeft)


class ChatView(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._container = QWidget()
        self._container.setObjectName("chatContainer")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(32, 18, 32, 18)
        self._layout.setSpacing(4)
        self._layout.addStretch(1)
        self.setWidget(self._container)

    # ------------------------------------------------------------------
    def _add(self, role: str, text: str, meta: str | None = None) -> None:
        if meta is None:
            ts = time.strftime("%H:%M:%S")
            meta = f"TS {ts}"
        block = _MessageBlock(text, role, meta)
        self._layout.insertWidget(self._layout.count() - 1, block)
        QTimer.singleShot(0, self._scroll_to_bottom)

    def add_user(self, text: str, voice: bool = False) -> None:
        ts = time.strftime("%H:%M:%S")
        meta = f"VOX // TS {ts}" if voice else f"TS {ts}"
        self._add("user", text, meta=meta)

    def add_assistant(self, text: str) -> None:
        self._add("assistant", text)

    def add_system(self, text: str) -> None:
        self._add("assistant", text, meta=f"SYS // TS {time.strftime('%H:%M:%S')}")

    def clear(self) -> None:
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _scroll_to_bottom(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())
