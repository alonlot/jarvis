"""Animated Stark-Industries-style arc reactor.

Outer ring with triangular segments (10 — same as the canonical Mk-I-era
reactor), several concentric inner rings, a bright repulsor core that
pulses with state, and angular tick marks. Used standalone in the floating
overlay and embedded in the main window."""
from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QPolygonF, QRadialGradient
from PyQt6.QtWidgets import QWidget


_STATE_COLORS = {
    "idle":       QColor(0,   212, 255),
    "listening":  QColor(123, 233, 255),
    "processing": QColor(180, 140, 255),
    "talking":    QColor(255, 170, 80),
}


class ArcReactorWidget(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None, *, size: int = 120, clickable: bool = False):
        super().__init__(parent)
        self.setFixedSize(QSize(size, size))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._state = "idle"
        self._phase = 0.0
        self._rotation = 0.0
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
            "idle": "READY",
            "listening": "LISTENING",
            "processing": "PROCESSING",
            "talking": "SPEAKING",
        }.get(self._state, self._state.upper())

    # ------------------------------------------------------------------
    def _tick(self) -> None:
        self._phase = (self._phase + 0.05) % (2 * math.pi)
        self._rotation = (self._rotation + 0.4) % 360
        # Always repaint so the slow outer rotation is visible even at idle.
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
        cx, cy = w / 2.0, h / 2.0
        r = min(w, h) / 2.0 - 4

        base = _STATE_COLORS.get(self._state, _STATE_COLORS["idle"])

        pulse = 0.0
        if self._state in {"listening", "talking"}:
            pulse = (math.sin(self._phase) + 1) / 2  # 0..1
        elif self._state == "idle":
            pulse = (math.sin(self._phase * 0.4) + 1) * 0.15  # subtle idle breathing

        # ── Outer atmospheric glow ────────────────────────────────────
        glow = QRadialGradient(cx, cy, r * 1.1)
        c0 = QColor(base); c0.setAlphaF(0.10 + 0.35 * pulse)
        c1 = QColor(base); c1.setAlphaF(0.0)
        glow.setColorAt(0.3, c0)
        glow.setColorAt(1.0, c1)
        p.setBrush(QBrush(glow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), r * 1.1, r * 1.1)

        # ── Outermost thin ring ───────────────────────────────────────
        pen_thin = QPen(base, max(1.0, r * 0.025))
        pen_thin.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen_thin)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)

        # ── Rotating tick marks (outside the outer ring) ──────────────
        ticks_pen = QPen(base, max(1.0, r * 0.018))
        ticks_pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(ticks_pen)
        n_ticks = 36
        rot_rad = math.radians(self._rotation)
        for i in range(n_ticks):
            a = (i / n_ticks) * 2 * math.pi + rot_rad
            is_major = (i % 9 == 0)
            t1 = r * (1.02)
            t2 = r * (1.12 if is_major else 1.07)
            x1, y1 = cx + t1 * math.cos(a), cy + t1 * math.sin(a)
            x2, y2 = cx + t2 * math.cos(a), cy + t2 * math.sin(a)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # ── 10 triangular segments (the iconic reactor wedges) ────────
        seg_color = QColor(base); seg_color.setAlphaF(0.85)
        seg_brush = QColor(base); seg_brush.setAlphaF(0.18 + 0.10 * pulse)
        seg_outer = r * 0.86
        seg_inner = r * 0.58
        n_seg = 10
        # Slow counter-rotation makes the segments feel mechanical.
        seg_rot = -rot_rad * 0.5
        gap = 0.045   # radians of gap between segments
        for i in range(n_seg):
            a0 = (i / n_seg) * 2 * math.pi + seg_rot + gap / 2
            a1 = ((i + 1) / n_seg) * 2 * math.pi + seg_rot - gap / 2
            # Trapezoid: outer arc edge points + inner arc edge points.
            poly = QPolygonF([
                QPointF(cx + seg_outer * math.cos(a0), cy + seg_outer * math.sin(a0)),
                QPointF(cx + seg_outer * math.cos(a1), cy + seg_outer * math.sin(a1)),
                QPointF(cx + seg_inner * math.cos(a1), cy + seg_inner * math.sin(a1)),
                QPointF(cx + seg_inner * math.cos(a0), cy + seg_inner * math.sin(a0)),
            ])
            p.setBrush(QBrush(seg_brush))
            p.setPen(QPen(seg_color, max(1.0, r * 0.012)))
            p.drawPolygon(poly)

        # ── Inner ring (bounding the segments on the inside) ──────────
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(base, max(1.5, r * 0.03)))
        p.drawEllipse(QPointF(cx, cy), r * 0.55, r * 0.55)

        # Slightly inner ring.
        thin = QColor(base); thin.setAlphaF(0.5)
        p.setPen(QPen(thin, max(1.0, r * 0.018)))
        p.drawEllipse(QPointF(cx, cy), r * 0.45, r * 0.45)

        # ── Processing spinner ────────────────────────────────────────
        if self._state == "processing":
            sp = QPen(base, max(3.0, r * 0.06))
            sp.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(sp)
            start = int((self._phase / (2 * math.pi)) * 360 * 16)
            arc_r = r * 0.72
            arc_rect = QRectF(cx - arc_r, cy - arc_r, 2 * arc_r, 2 * arc_r)
            p.drawArc(arc_rect, start, 110 * 16)

        # ── Repulsor core ─────────────────────────────────────────────
        # Bright bloom behind the core.
        bloom = QRadialGradient(cx, cy, r * 0.38)
        bc0 = QColor(base); bc0.setAlphaF(0.55 + 0.35 * pulse)
        bc1 = QColor(base); bc1.setAlphaF(0.0)
        bloom.setColorAt(0.0, bc0)
        bloom.setColorAt(1.0, bc1)
        p.setBrush(QBrush(bloom))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), r * 0.38, r * 0.38)

        # Solid core disc.
        core_r = r * (0.22 + 0.05 * pulse)
        core_grad = QRadialGradient(cx - core_r * 0.25, cy - core_r * 0.35, core_r * 1.4)
        core_grad.setColorAt(0.0, QColor(255, 255, 255, 250))
        core_grad.setColorAt(0.45, QColor(base.red(), base.green(), base.blue(), 230))
        core_grad.setColorAt(1.0, QColor(base.red() // 2, base.green() // 2, base.blue(), 200))
        p.setBrush(QBrush(core_grad))
        p.setPen(QPen(base, max(1.0, r * 0.015)))
        p.drawEllipse(QPointF(cx, cy), core_r, core_r)

        # Cross-hair inside the core (Mk-style detail).
        ch = QColor(255, 255, 255); ch.setAlphaF(0.55 + 0.30 * pulse)
        p.setPen(QPen(ch, max(0.8, r * 0.012)))
        p.drawLine(QPointF(cx - core_r * 0.55, cy), QPointF(cx + core_r * 0.55, cy))
        p.drawLine(QPointF(cx, cy - core_r * 0.55), QPointF(cx, cy + core_r * 0.55))
