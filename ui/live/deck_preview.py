import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QPainter, QPen, QFont

from ui.shared_widgets import frame_to_pixmap


class DeckPreview(QWidget):
    def __init__(self, side: str, parent=None):
        super().__init__(parent)
        self.side = side
        self.setStyleSheet("background-color: #111111;")
        self.setMinimumHeight(160)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(2)

        header = QLabel(f"DECK {side}")
        header.setAlignment(Qt.AlignHCenter)
        header.setStyleSheet(
            "color: #666666; font-family: 'terminal grotesque'; font-weight: bold; "
            "font-size: 12px; background: transparent;"
        )
        lay.addWidget(header, 0, alignment=Qt.AlignTop | Qt.AlignHCenter)

        self._frame_lbl = QLabel()
        self._frame_lbl.setAlignment(Qt.AlignCenter)
        self._frame_lbl.setStyleSheet("background: transparent;")
        self._frame_lbl.hide()
        lay.addWidget(self._frame_lbl, 1)

        self._empty_lbl = QLabel("— no content —")
        self._empty_lbl.setAlignment(Qt.AlignCenter)
        self._empty_lbl.setStyleSheet(
            "color: #333333; font-family: 'terminal grotesque'; font-size: 11px; background: transparent;"
        )
        lay.addWidget(self._empty_lbl, 1)

    @Slot(object)
    def update_frame(self, frame: np.ndarray):
        self._empty_lbl.hide()
        self._frame_lbl.show()

        pixmap = frame_to_pixmap(frame)
        lbl_size = self._frame_lbl.size()
        if lbl_size.width() > 0 and lbl_size.height() > 0:
            pixmap = pixmap.scaled(lbl_size, Qt.KeepAspectRatio, Qt.FastTransformation)

        self._frame_lbl.setPixmap(pixmap)


class _FpsRuler(QWidget):
    _MARKS    = [15, 30, 45]
    _VMIN     = 1
    _VMAX     = 60
    _HANDLE_H = 12

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(28)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        h       = self.height()
        half_h  = self._HANDLE_H // 2
        track_h = h - 2 * half_h
        vrange  = self._VMAX - self._VMIN

        pen = QPen(QColor("#777777"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setFont(QFont("terminal grotesque", 7))

        for val in self._MARKS:
            ratio = (val - self._VMIN) / vrange
            y = h - half_h - int(ratio * track_h)
            painter.drawLine(2, y, 6, y)
            painter.setPen(QColor("#666666"))
            painter.drawText(8, y + 4, str(val))
            painter.setPen(pen)
