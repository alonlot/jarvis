"""HUD chrome — corner-bracket frame + animated top status bar."""
from __future__ import annotations

import time

from PyQt6.QtCore import QPointF, QRect, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..styles import PALETTE


class BracketFrame(QWidget):
    """Wraps a child widget in HUD corner brackets — `┌  ┐  └  ┘` style."""

    def __init__(self, child: QWidget, *, bracket_size: int = 10,
                 role: str = "assistant", parent=None):
        super().__init__(parent)
        self._bracket_size = bracket_size
        self._role = role
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.addWidget(child)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(PALETTE["cyan"]) if self._role == "assistant" else QColor(PALETTE["cyan_glow"])
        pen = QPen(color, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(pen)

        bs = self._bracket_size
        w, h = self.width() - 1, self.height() - 1

        # Top-left.
        p.drawLine(QPointF(0, 0), QPointF(bs, 0))
        p.drawLine(QPointF(0, 0), QPointF(0, bs))
        # Top-right.
        p.drawLine(QPointF(w, 0), QPointF(w - bs, 0))
        p.drawLine(QPointF(w, 0), QPointF(w, bs))
        # Bottom-left.
        p.drawLine(QPointF(0, h), QPointF(bs, h))
        p.drawLine(QPointF(0, h), QPointF(0, h - bs))
        # Bottom-right.
        p.drawLine(QPointF(w, h), QPointF(w - bs, h))
        p.drawLine(QPointF(w, h), QPointF(w, h - bs))


class HudStatusBar(QWidget):
    """Thin top bar with rotating system telemetry — like a HUD readout.

    Shows: corner code, system status (online/listening/etc), memory count,
    backend in use, clock. Refreshes every second.
    """

    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.setObjectName("hudBar")
        self.setFixedHeight(28)

        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        self.left = QLabel("◢ J.A.R.V.I.S // SYS_LINK_v1")
        self.left.setObjectName("hudCorner")
        h.addWidget(self.left)

        h.addStretch(1)

        self.center = QLabel("SYSTEM ONLINE")
        self.center.setObjectName("hudStatus")
        self.center.setProperty("severity", "ok")
        h.addWidget(self.center)

        h.addStretch(1)

        self.right = QLabel("--:--:--")
        self.right.setObjectName("hudCorner")
        h.addWidget(self.right)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(1000)
        self._refresh()

    # ------------------------------------------------------------------
    def set_status(self, text: str, severity: str = "ok") -> None:
        self.center.setText(text.upper())
        self.center.setProperty("severity", severity)
        # Re-polish to apply the property-based stylesheet selector.
        self.center.style().unpolish(self.center)
        self.center.style().polish(self.center)

    def _refresh(self) -> None:
        # Right corner: telemetry triad — clock | memory | backend
        cfg = self.assistant.config
        backend = cfg.get("llm.backend", "claude_cli").upper()
        if backend == "OPENAI_COMPAT":
            backend = f"API:{cfg.get('llm.openai_compat.model', '').upper()[:14]}"
        else:
            backend = "CLAUDE -P"
        stats = self.assistant.memory.stats()
        clock = time.strftime("%H:%M:%S")
        self.right.setText(
            f"MEM:{stats['total_facts']:03d}  "
            f"BACKEND:{backend}  "
            f"◤ {clock}"
        )


class CornerHudOverlay(QWidget):
    """Decorative outer corner brackets that frame the whole window — a
    constant reminder that you're inside Stark Industries kit."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        parent.installEventFilter(self)
        self._update_geometry()

    def eventFilter(self, obj, event):
        if event.type() == event.Type.Resize:
            self._update_geometry()
        return False

    def _update_geometry(self) -> None:
        parent = self.parentWidget()
        if parent:
            self.setGeometry(QRect(0, 0, parent.width(), parent.height()))
            self.raise_()
            self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(PALETTE["cyan"]), 1.5)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(pen)

        bs = 22
        w, h = self.width() - 1, self.height() - 1

        # Corner brackets — drawn just inside the window edges.
        m = 6
        # Top-left.
        p.drawLine(QPointF(m, m), QPointF(m + bs, m))
        p.drawLine(QPointF(m, m), QPointF(m, m + bs))
        # Top-right.
        p.drawLine(QPointF(w - m, m), QPointF(w - m - bs, m))
        p.drawLine(QPointF(w - m, m), QPointF(w - m, m + bs))
        # Bottom-left.
        p.drawLine(QPointF(m, h - m), QPointF(m + bs, h - m))
        p.drawLine(QPointF(m, h - m), QPointF(m, h - m - bs))
        # Bottom-right.
        p.drawLine(QPointF(w - m, h - m), QPointF(w - m - bs, h - m))
        p.drawLine(QPointF(w - m, h - m), QPointF(w - m, h - m - bs))
