import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Slot, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap

_STYLE = """
QWidget#outputRoot {
    background-color: #000000;
}
QLabel#title {
    color: white;
    font-family: 'terminal grotesque', monospace;
    font-size: 12px;
    font-weight: bold;
}
QLabel#sampling {
    color: white;
    font-family: 'terminal grotesque', monospace;
    font-size: 11px;
    padding: 4px;
}
QPushButton#broadcastBtn {
    background-color: #333333;
    color: #888888;
    border: 1px solid #555555;
    padding: 4px 12px;
    font-family: 'terminal grotesque', monospace;
    font-size: 11px;
    font-weight: bold;
}
QPushButton#broadcastBtn:checked {
    background-color: #1a5c2a;
    color: #33ff55;
    border: 1px solid #33ff55;
}
"""


class OutputWindow(QWidget):
    broadcast_changed = Signal(bool)   # replaces direct _broadcast_btn.toggled access

    def __init__(self, config):
        super().__init__(None, Qt.Window)
        self.config = config
        self.setWindowTitle("OUTPUT — SendPix3")
        self.resize(640, 480)
        self.setObjectName("outputRoot")
        self.setStyleSheet(_STYLE)

        self._current_frame: np.ndarray | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        top = QHBoxLayout()
        title = QLabel("OUTPUT")
        title.setObjectName("title")
        top.addWidget(title)
        top.addStretch()

        self._broadcast_btn = QPushButton("BROADCAST OFF")
        self._broadcast_btn.setObjectName("broadcastBtn")
        self._broadcast_btn.setCheckable(True)
        self._broadcast_btn.toggled.connect(self._on_broadcast_toggled)
        top.addWidget(self._broadcast_btn)
        layout.addLayout(top)

        self._display = QLabel()
        self._display.setAlignment(Qt.AlignCenter)
        self._display.setStyleSheet("background-color: #000000;")
        self._display.setMinimumSize(200, 150)
        layout.addWidget(self._display, 1)

        self._sampling_lbl = QLabel("")
        self._sampling_lbl.setObjectName("sampling")
        layout.addWidget(self._sampling_lbl)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(10)
        self._refresh_timer.timeout.connect(self._refresh)
        self._refresh_timer.start()

    def _on_broadcast_toggled(self, checked: bool):
        self._broadcast_btn.setText("BROADCAST ON" if checked else "BROADCAST OFF")
        self.broadcast_changed.emit(checked)

    def set_frame(self, frame: np.ndarray):
        """Called directly from RenderEngine thread via DirectConnection — store only."""
        self._current_frame = frame   # GIL makes this assignment atomic

    def _refresh(self):
        if self._current_frame is None:
            return
        frame = self._current_frame
        h, w = frame.shape[:2]
        dw = self._display.width() or 640
        dh = self._display.height() or 480
        scale = max(1, min(dw // max(w, 1), dh // max(h, 1)))

        upscaled = np.repeat(np.repeat(frame, scale, axis=0), scale, axis=1)
        uh, uw = upscaled.shape[:2]

        img = QImage(upscaled.data, uw, uh, uw * 3, QImage.Format_RGB888)
        self._display.setPixmap(QPixmap.fromImage(img.copy()))

    def set_interpolation(self, mode: str):
        self._sampling_lbl.setText(f"sampling: {mode}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()
