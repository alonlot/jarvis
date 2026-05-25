"""Frameless always-on-top Jarvis overlay — a draggable arc reactor."""
from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QMouseEvent
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from ..core.config import Config
from .widgets.arc_reactor import ArcReactorWidget


class JarvisOverlay(QWidget):
    clicked = pyqtSignal()

    def __init__(self, cfg: Config):
        super().__init__(None)
        self.cfg = cfg

        size = int(cfg.get("overlay.size_px", 96))
        self.setFixedSize(size, size)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.reactor = ArcReactorWidget(self, size=size, clickable=False)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.reactor)

        self._position_self()
        self._drag_pos: QPoint | None = None
        self._press_pos: QPoint | None = None

    # ------------------------------------------------------------------
    def set_state(self, state: str) -> None:
        self.reactor.set_state(state)

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
        else:
            x, y = avail.right() - w - margin, avail.bottom() - h - margin
        self.move(x, y)

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
