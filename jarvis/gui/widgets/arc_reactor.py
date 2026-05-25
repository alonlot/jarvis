"""Animated arc-reactor widget. Used standalone in the overlay and embedded
in the main chat window header. Four states: idle / listening / processing /
talking. Pulses and color shifts reflect the state."""
from __future__ import annotations

import math

from PyQt6.QtCore import QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import QWidget


_STATE_COLORS = {
    "idle":       QColor(64, 200, 255),
    "listening":  QColor(80, 240, 255),
    "processing": QColor(180, 140, 255),
    "talking":    QColor(255, 170, 80),
}


class ArcReactorWidget(QWidget):
    """Square widget that paints a glowing arc reactor.

    Set `state` to one of {idle, listening, processing, talking}.
    Set `clickable=True` and connect to .clicked to use as a button.
    """

    clicked = pyqtSignal()

    def __init__(self, parent=None, *, size: int = 96, clickable: bool = False):
        super().__init__(parent)
        self.setFixedSize(QSize(size, size))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._state = "idle"
        self._phase = 0.0
        self._clickable = clickable
        if clickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    # ------------------------------------------------------------------
    def set_state(self, state: str) -> None:
        if state in _STATE_COLORS and state != self._state:
            self._state = state
            self.update()

    @property
    def state(self) -> str:
        return self._state

    def state_label(self) -> str:
        return {
            "idle": "Ready, sir.",
            "listening": "Listening…",
            "processing": "Thinking…",
            "talking": "Speaking…",
        }.get(self._state, self._state)

    # ------------------------------------------------------------------
    def _tick(self) -> None:
        self._phase = (self._phase + 0.05) % (2 * math.pi)
        if self._state != "idle":
            self.update()

    def mousePressEvent(self, e) -> None:
        if self._clickable and e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            e.accept()
            return
        super().mousePressEvent(e)

    # ------------------------------------------------------------------
    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) / 2 - 6

        base = _STATE_COLORS.get(self._state, _STATE_COLORS["idle"])

        pulse = 0.0
        if self._state in {"listening", "talking"}:
            pulse = (math.sin(self._phase) + 1) / 2

        # Outer glow.
        glow = QRadialGradient(cx, cy, r)
        c0 = QColor(base); c0.setAlphaF(0.10 + 0.30 * pulse)
        c1 = QColor(base); c1.setAlphaF(0.0)
        glow.setColorAt(0.4, c0)
        glow.setColorAt(1.0, c1)
        p.setBrush(QBrush(glow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(int(cx - r), int(cy - r), int(2 * r), int(2 * r))

        # Outer ring.
        pen = QPen(base, max(2.0, r * 0.04))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(int(cx - r), int(cy - r), int(2 * r), int(2 * r))

        # Inner ring.
        p.drawEllipse(int(cx - r * 0.55), int(cy - r * 0.55),
                      int(r * 1.1), int(r * 1.1))

        # Tick marks around outer ring.
        ticks = 12
        tick_pen = QPen(base, max(1.0, r * 0.02))
        p.setPen(tick_pen)
        for i in range(ticks):
            a = (i / ticks) * 2 * math.pi
            x1, y1 = cx + (r - 2) * math.cos(a), cy + (r - 2) * math.sin(a)
            x2, y2 = cx + (r - r * 0.18) * math.cos(a), cy + (r - r * 0.18) * math.sin(a)
            p.drawLine(int(x1), int(y1), int(x2), int(y2))

        # Processing spinner.
        if self._state == "processing":
            sp = QPen(base, max(3.0, r * 0.06))
            p.setPen(sp)
            start = int((self._phase / (2 * math.pi)) * 360 * 16)
            p.drawArc(int(cx - r * 0.75), int(cy - r * 0.75),
                      int(r * 1.5), int(r * 1.5), start, 90 * 16)

        # Center core (the "beating" heart).
        core = QColor(base); core.setAlphaF(0.85 + 0.15 * pulse)
        p.setBrush(QBrush(core))
        p.setPen(Qt.PenStyle.NoPen)
        cr = r * (0.20 + 0.06 * pulse)
        p.drawEllipse(int(cx - cr), int(cy - cr), int(2 * cr), int(2 * cr))

        # Inner highlight.
        hi = QColor(255, 255, 255); hi.setAlphaF(0.20 + 0.30 * pulse)
        p.setBrush(QBrush(hi))
        hr = cr * 0.45
        p.drawEllipse(int(cx - hr * 1.2), int(cy - hr * 1.6),
                      int(hr * 1.6), int(hr * 1.2))
