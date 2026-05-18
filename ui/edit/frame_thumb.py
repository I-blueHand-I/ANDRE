import numpy as np
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QPainter, QImage, QColor, QPen

from ui.theme import ACCENT as _ACCENT

_THUMB_H     = 72
_THUMB_PREV  = 60
_THUMB_LABEL = _THUMB_H - _THUMB_PREV


class _FrameThumb(QWidget):
    clicked          = Signal(int)
    delete_requested = Signal(int)

    _BORDER = 2

    def __init__(self, index: int, pixels: np.ndarray, selected: bool = False, parent=None):
        super().__init__(parent)
        self.index     = index
        self._pixels   = pixels
        self._selected = selected
        self.setFixedHeight(_THUMB_H)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)

    def set_selected(self, v: bool):
        self._selected = v
        self.update()

    def set_pixels(self, arr: np.ndarray):
        self._pixels = arr
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.index)
        elif event.button() == Qt.RightButton:
            self.delete_requested.emit(self.index)

    def paintEvent(self, event):
        w = self.width()
        b = self._BORDER
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        border_col = QColor(_ACCENT) if self._selected else QColor("#444444")
        painter.fillRect(0, 0, w, _THUMB_PREV, border_col)
        painter.fillRect(b, b, w - 2*b, _THUMB_PREV - 2*b, QColor("#111111"))

        if self._pixels is not None and self._pixels.any():
            arr = np.ascontiguousarray(self._pixels)
            H, W = arr.shape[:2]
            img  = QImage(arr.data, W, H, W * 3, QImage.Format_RGB888)
            painter.drawImage(QRect(b, b, w - 2*b, _THUMB_PREV - 2*b), img)

        painter.fillRect(0, _THUMB_PREV, w, _THUMB_LABEL, QColor("#1a1a1a"))
        painter.setPen(QColor(_ACCENT) if self._selected else QColor("#666666"))
        font = painter.font()
        font.setPointSize(6)
        font.setFamily("Courier New")
        painter.setFont(font)
        painter.drawText(QRect(0, _THUMB_PREV, w, _THUMB_LABEL),
                         Qt.AlignCenter, str(self.index + 1))


class _AddFrameThumb(QWidget):
    def __init__(self, callback, parent=None):
        super().__init__(parent)
        self._callback = callback
        self._hovered  = False
        self.setFixedHeight(_THUMB_H)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._callback()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def paintEvent(self, event):
        w       = self.width()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        bg = QColor("#1e1e1e") if self._hovered else QColor("#111111")
        painter.fillRect(0, 0, w, _THUMB_PREV, bg)

        pen = QPen(QColor("#999999") if self._hovered else QColor("#606060"))
        pen.setWidth(1)
        pen.setDashPattern([5, 6])
        painter.setPen(pen)
        painter.drawRect(2, 2, w - 5, _THUMB_PREV - 5)

        painter.setPen(QColor("#cccccc") if self._hovered else QColor("#606060"))
        font = painter.font()
        font.setPointSize(18)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRect(0, 0, w, _THUMB_PREV), Qt.AlignCenter, "+")

        painter.fillRect(0, _THUMB_PREV, w, _THUMB_LABEL, QColor("#1a1a1a"))
