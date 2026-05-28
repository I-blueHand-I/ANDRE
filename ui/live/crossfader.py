from PySide6.QtWidgets import QSlider
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QStyleOptionSlider, QStyle

from ui.theme import ACCENT as _ACCENT


class _CrossfaderSlider(QSlider):
    _GROOVE_H   = 4
    _HANDLE_W   = 14
    _HANDLE_H   = 14
    _COL_FILL   = QColor(_ACCENT)
    _COL_TRACK  = QColor("#3a3a3a")
    _COL_HANDLE = QColor(_ACCENT)

    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setRange(0, 100)
        self.setValue(50)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        opt = QStyleOptionSlider()
        self.initStyleOption(opt)

        groove = self.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self)
        handle = self.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, self)

        gy   = groove.center().y()
        half = self._GROOVE_H // 2

        painter.fillRect(groove.left(), gy - half, groove.width(), self._GROOVE_H, self._COL_TRACK)

        cx = groove.center().x()
        hx = handle.center().x()
        if hx != cx:
            x1, x2 = (cx, hx) if hx > cx else (hx, cx)
            painter.fillRect(x1, gy - half, x2 - x1, self._GROOVE_H, self._COL_FILL)

        hw  = self._HANDLE_W
        hh  = self._HANDLE_H
        hx2 = handle.center().x() - hw // 2
        hy2 = handle.center().y() - hh // 2
        painter.fillRect(hx2, hy2, hw, hh, self._COL_HANDLE)
