"""Frameless always-on-top Jarvis overlay — a glowing arc reactor.

Three states:
  - idle:       quiet cyan ring
  - listening:  pulsing brighter, animated
  - processing: spinning arc
  - talking:    pulsing warm
"""
from __future__ import annotations

import math

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QGuiApplication, QMouseEvent, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import QWidget

from ..core.config import Config


class JarvisOverlay(QWidget):
    clicked = pyqtSignal()

    def __init__(self, cfg: Config):
        super().__init__(None)
        self.cfg = cfg
        self.state = "idle"
        self._phase = 0.0

        size = int(cfg.get("overlay.size_px", 96))
        self.setFixedSize(QSize(size, size))

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._position_self()

        self._drag_pos: QPoint | None = None
        self._press_pos: QPoint | None = None

        # Animation tick.
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    # ------------------------------------------------------------------
    def set_state(self, state: str) -> None:
        if state in {"idle", "listening", "processing", "talking"}:
            self.state = state
            self.update()

    # ------------------------------------------------------------------
    def _position_self(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return
        avail: QRect = screen.availableGeometry()
        margin = int(self.cfg.get("overlay.margin_px", 24))
        pos = self.cfg.get("overlay.position", "bottom_right")
        w, h = self.width(), self.height()
        if pos == "top_left":
            x, y = avail.x() + margin, avail.y() + margin
        elif pos == "top_right":
            x, y = avail.right() - w - margin, avail.y() + margin
        elif pos == "bottom_left":
            x, y = avail.x() + margin, avail.bottom() - h - margin
        else:  # bottom_right default
            x, y = avail.right() - w - margin, avail.bottom() - h - margin
        self.move(x, y)

    # ------------------------------------------------------------------
    def _tick(self) -> None:
        self._phase = (self._phase + 0.05) % (2 * math.pi)
        if self.state in {"listening", "processing", "talking"}:
            self.update()

    # ------------------------------------------------------------------
    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) / 2 - 6

        # Core color by state.
        base = QColor(64, 200, 255)
        if self.state == "listening":
            base = QColor(80, 240, 255)
        elif self.state == "processing":
            base = QColor(180, 140, 255)
        elif self.state == "talking":
            base = QColor(255, 170, 80)

        pulse = 0.0
        if self.state in {"listening", "talking"}:
            pulse = (math.sin(self._phase) + 1) / 2  # 0..1

        # Outer glow (radial gradient).
        glow = QRadialGradient(cx, cy, r)
        glow_c = QColor(base)
        glow_c.setAlphaF(0.10 + 0.25 * pulse)
        glow.setColorAt(0.4, glow_c)
        glow_c2 = QColor(base); glow_c2.setAlphaF(0)
        glow.setColorAt(1.0, glow_c2)
        p.setBrush(QBrush(glow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(int(cx - r), int(cy - r), int(2 * r), int(2 * r))

        # Outer ring.
        pen = QPen(base, 2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(int(cx - r), int(cy - r), int(2 * r), int(2 * r))

        # Inner ring.
        p.drawEllipse(int(cx - r * 0.55), int(cy - r * 0.55), int(r * 1.1), int(r * 1.1))

        # Processing spinner.
        if self.state == "processing":
            spinner_pen = QPen(base, 3)
            p.setPen(spinner_pen)
            start = int((self._phase / (2 * math.pi)) * 360 * 16)
            p.drawArc(int(cx - r * 0.75), int(cy - r * 0.75),
                      int(r * 1.5), int(r * 1.5), start, 90 * 16)

        # Center dot.
        core = QColor(base); core.setAlphaF(0.85 + 0.15 * pulse)
        p.setBrush(QBrush(core))
        p.setPen(Qt.PenStyle.NoPen)
        cr = r * (0.18 + 0.04 * pulse)
        p.drawEllipse(int(cx - cr), int(cy - cr), int(2 * cr), int(2 * cr))

    # ------------------------------------------------------------------
    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._press_pos = e.globalPosition().toPoint()
            self._drag_pos = self._press_pos - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        if e.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
            e.accept()

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.MouseButton.LeftButton and self._press_pos:
            travel = (e.globalPosition().toPoint() - self._press_pos).manhattanLength()
            if travel < 5 and self.cfg.get("overlay.click_to_talk", True):
                self.clicked.emit()
        self._press_pos = None
        self._drag_pos = None
