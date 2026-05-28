from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QSpinBox, QPushButton, QWidget, QFileDialog, QComboBox
)
from PySide6.QtCore import Qt

from midi.midi_manager import get_midi_ports

_STYLE = """
QDialog {
    background-color: #2a2a2a;
}
QLabel {
    color: white;
    font-family: 'terminal grotesque', monospace;
    font-size: 13px;
    font-weight: bold;
}
QLabel#title {
    font-size: 20px;
    font-weight: bold;
    margin-bottom: 8px;
}
QLineEdit, QSpinBox {
    background-color: #1a1a1a;
    color: white;
    border: 1px solid #555555;
    padding: 5px 10px;
    font-family: 'terminal grotesque', monospace;
    font-size: 13px;
    min-width: 80px;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #3a3a3a;
    border: none;
    width: 18px;
}
QComboBox {
    background-color: #1a1a1a;
    color: white;
    border: 1px solid #555555;
    padding: 5px 10px;
    font-family: 'terminal grotesque', monospace;
    font-size: 13px;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #1a1a1a;
    color: white;
    selection-background-color: #333333;
    border: 1px solid #555555;
}
QPushButton#sendpix {
    background-color: #ffffff;
    color: #000000;
    border: none;
    padding: 16px;
    font-family: 'terminal grotesque', monospace;
    font-size: 17px;
    font-weight: bold;
    margin-top: 12px;
}
QPushButton#sendpix:hover {
    background-color: #e0e0e0;
}
QPushButton#browse {
    background-color: #3a3a3a;
    color: white;
    border: 1px solid #666666;
    padding: 4px 8px;
    font-size: 11px;
    min-width: 28px;
}
QPushButton#browse:hover {
    background-color: #4a4a4a;
}
"""


class ConfigDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("SETTINGS")
        self.setModal(True)
        self.setMinimumWidth(540)
        self.setStyleSheet(_STYLE)
        self._build_ui()
        self._load()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(0)

        title = QLabel("SETTINGS")
        title.setObjectName("title")
        root.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(14)
        grid.setColumnStretch(1, 1)

        # RESOLUTION
        grid.addWidget(QLabel("RESOLUTION"), 0, 0)
        res_box = QWidget()
        res_lay = QHBoxLayout(res_box)
        res_lay.setContentsMargins(0, 0, 0, 0)
        res_lay.setSpacing(8)
        self.led_w = QSpinBox()
        self.led_w.setRange(1, 512)
        self.led_w.setFixedWidth(70)
        self.led_h = QSpinBox()
        self.led_h.setRange(1, 512)
        self.led_h.setFixedWidth(70)
        sep = QLabel("×")
        sep.setStyleSheet("color: #888;")
        res_lay.addWidget(self.led_w)
        res_lay.addWidget(sep)
        res_lay.addWidget(self.led_h)
        res_lay.addStretch()
        grid.addWidget(res_box, 0, 1)

        # UDP PORT
        grid.addWidget(QLabel("UDP PORT"), 1, 0)
        self.udp_port = QSpinBox()
        self.udp_port.setRange(1, 65535)
        self.udp_port.setFixedWidth(90)
        grid.addWidget(self.udp_port, 1, 1)

        # UDP ADDRESS
        grid.addWidget(QLabel("UDP ADDRESS"), 2, 0)
        self.udp_addr = QLineEdit()
        grid.addWidget(self.udp_addr, 2, 1)

        # ANIMATIONS FOLDER
        grid.addWidget(QLabel("ANIMATIONS FOLDER"), 3, 0)
        grid.addWidget(self._folder_row("anim"), 3, 1)

        # MP4 FOLDER
        grid.addWidget(QLabel("MP4 FOLDER"), 4, 0)
        grid.addWidget(self._folder_row("mp4"), 4, 1)

        # MIDI INPUT
        grid.addWidget(QLabel("MIDI INPUT"), 5, 0)
        midi_ports = get_midi_ports()
        self.midi_combo = QComboBox()
        self.midi_combo.addItem("(no device)")
        self.midi_combo.addItems(midi_ports)
        if not midi_ports:
            self.midi_combo.setEnabled(False)
            self.midi_combo.setToolTip("Install python-rtmidi to enable MIDI")
        grid.addWidget(self.midi_combo, 5, 1)

        root.addSpacing(8)
        root.addLayout(grid)

        send = QPushButton("SEND PIX !")
        send.setObjectName("sendpix")
        send.clicked.connect(self._apply)
        root.addWidget(send)

    def _folder_row(self, key: str) -> QWidget:
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        edit = QLineEdit()
        btn = QPushButton("…")
        btn.setObjectName("browse")
        btn.setFixedWidth(32)
        if key == "anim":
            self.anim_folder = edit
            btn.clicked.connect(self._browse_anim)
        else:
            self.mp4_folder = edit
            btn.clicked.connect(self._browse_mp4)
        lay.addWidget(edit, 1)
        lay.addWidget(btn)
        return box

    def _load(self):
        res = self.config.get("led_resolution", [21, 16])
        self.led_w.setValue(res[0])
        self.led_h.setValue(res[1])
        self.udp_port.setValue(self.config.get("udp_port", 37020))
        self.udp_addr.setText(self.config.get("udp_address", "255.255.255.255"))
        self.anim_folder.setText(self.config.get("animations_folder", ""))
        self.mp4_folder.setText(self.config.get("mp4_folder", ""))
        device = self.config.get("midi_device", "")
        idx = self.midi_combo.findText(device)
        if idx >= 0:
            self.midi_combo.setCurrentIndex(idx)

    def _apply(self):
        self.config.set("led_resolution", [self.led_w.value(), self.led_h.value()])
        self.config.set("udp_port", self.udp_port.value())
        self.config.set("udp_address", self.udp_addr.text().strip())
        self.config.set("animations_folder", self.anim_folder.text().strip())
        self.config.set("mp4_folder", self.mp4_folder.text().strip())
        selected = self.midi_combo.currentText()
        self.config.set("midi_device", "" if selected == "(no device)" else selected)
        self.accept()

    def _browse_anim(self):
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner le dossier animations")
        if folder:
            self.anim_folder.setText(folder)

    def _browse_mp4(self):
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner le dossier MP4")
        if folder:
            self.mp4_folder.setText(folder)
