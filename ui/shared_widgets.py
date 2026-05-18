import math as _math

import numpy as np
from PySide6.QtWidgets import QDial
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QBrush, QImage, QPixmap


def frame_to_pixmap(frame: np.ndarray) -> QPixmap:
    """Convert an (H, W, 3) uint8 RGB numpy array to a QPixmap."""
    h, w = frame.shape[:2]
    rgb = np.ascontiguousarray(frame)
    img = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
    return QPixmap.fromImage(img.copy())


class ColorDial(QDial):
    """Cercle coloré avec point noir comme indicateur de position (7h→5h, 270°)."""

    def __init__(self, rgb_color: str, parent=None):
        super().__init__(parent)
        self._color = QColor(rgb_color)
        self.setNotchesVisible(False)
        self.setRange(0, 255)
        self.setValue(0)
        self.setFixedSize(40, 40)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.35)
        rect = self.contentsRect()
        cx, cy = rect.center().x(), rect.center().y()
        r = min(rect.width(), rect.height()) / 2 - 1

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(self._color))
        p.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))

        ratio = (self.value() - self.minimum()) / max(1, self.maximum() - self.minimum())
        angle = _math.radians((360 - (135 + ratio * 270)) % 360)
        dr = r * 0.60
        dx = cx + dr * _math.cos(angle)
        dy = cy - dr * _math.sin(angle)
        ds = max(3, int(r * 0.22))
        p.setBrush(QBrush(QColor(0, 0, 0, 220)))
        p.drawEllipse(int(dx - ds), int(dy - ds), ds * 2, ds * 2)
        p.end()
