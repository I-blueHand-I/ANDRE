from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider
)
from PySide6.QtCore import Qt, Signal

from ui.mixette.styles import _label, _slider_style, _MIDI_BTN, _HUE_TOGGLE


class _MidiPanel(QWidget):
    """Base class for panels that contain MIDI-bindable controls.
    Manages the 'waiting…' / 'midi bind' button state and learn tracking."""

    midi_learn_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_btn: QPushButton | None = None

    def on_learn_bound(self, _control_name: str):
        if self._active_btn is not None:
            self._active_btn.blockSignals(True)
            self._active_btn.setChecked(False)
            self._active_btn.setText("midi bind")
            self._active_btn.blockSignals(False)
            self._active_btn = None

    def _make_learn_btn(self, name: str) -> QPushButton:
        btn = QPushButton("midi bind")
        btn.setCheckable(True)
        btn.setStyleSheet(_MIDI_BTN)
        btn.toggled.connect(lambda checked, b=btn: self._on_toggled(b, checked, name))
        return btn

    def _on_toggled(self, btn: QPushButton, checked: bool, name: str):
        if checked:
            if self._active_btn and self._active_btn is not btn:
                self._active_btn.blockSignals(True)
                self._active_btn.setChecked(False)
                self._active_btn.blockSignals(False)
            self._active_btn = btn
            btn.setText("waiting…")
            self.midi_learn_requested.emit(name)
        else:
            if self._active_btn is btn:
                self._active_btn = None
            btn.setText("midi bind")
            self.midi_learn_requested.emit("")


class RGBPanel(_MidiPanel):
    """Trois sliders R/G/B appliqués à l'output (0–255, neutre = 255)."""

    rgb_changed = Signal(float, float, float)   # r, g, b ∈ [0.0, 1.0]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(20)
        self._slider_r = self._add_row(lay, "RED",   "#440000", "#cc2222")
        self._slider_g = self._add_row(lay, "GREEN", "#004400", "#22aa22")
        self._slider_b = self._add_row(lay, "BLUE",  "#000044", "#2244cc")
        lay.addStretch(1)
        self._slider_r.valueChanged.connect(self._emit)
        self._slider_g.valueChanged.connect(self._emit)
        self._slider_b.valueChanged.connect(self._emit)

    def _add_row(self, parent_lay: QVBoxLayout, name: str,
                 track: str, fill: str) -> QSlider:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)

        header = QHBoxLayout()
        header.addWidget(_label(name))
        header.addStretch()
        header.addWidget(self._make_learn_btn(name))
        lay.addLayout(header)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 255)
        slider.setValue(255)
        slider.setStyleSheet(_slider_style(track, fill))
        lay.addWidget(slider)

        parent_lay.addWidget(w)
        return slider

    def _emit(self):
        self.rgb_changed.emit(
            self._slider_r.value() / 255.0,
            self._slider_g.value() / 255.0,
            self._slider_b.value() / 255.0,
        )


class HSVPanel(_MidiPanel):
    """
    HUE  : toggle ON/OFF + slider 0–360°  (shift de teinte, désactivable)
    SAT  : slider 0–255  (0 = niveaux de gris, 255 = saturation native)
    VALUE: slider 0–255  (0 = noir, 255 = luminosité native)
    """

    hsv_changed = Signal(bool, float, float, float)  # hue_on, hue_deg, sat, val

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(20)
        self._slider_h = self._add_hue_row(lay)
        self._slider_s = self._add_row(lay, "SATURATION", "#444444", "#888888")
        self._slider_v = self._add_row(lay, "VALUE",      "#444444", "#888888")
        lay.addStretch(1)
        self._slider_h.valueChanged.connect(self._emit)
        self._slider_s.valueChanged.connect(self._emit)
        self._slider_v.valueChanged.connect(self._emit)

    def _add_hue_row(self, parent_lay: QVBoxLayout) -> QSlider:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)

        header = QHBoxLayout()
        header.addWidget(_label("HUE"))
        header.addStretch()

        self._hue_toggle = QPushButton("OFF")
        self._hue_toggle.setCheckable(True)
        self._hue_toggle.setFixedWidth(40)
        self._hue_toggle.setStyleSheet(_HUE_TOGGLE)
        self._hue_toggle.toggled.connect(self._on_hue_toggle)
        header.addWidget(self._hue_toggle)
        header.addWidget(self._make_learn_btn("TOGGLE_HUE"))
        header.addWidget(self._make_learn_btn("HUE"))
        lay.addLayout(header)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 360)
        slider.setValue(0)
        slider.setStyleSheet(_slider_style("#444444", "#888888"))
        slider.setEnabled(False)
        lay.addWidget(slider)

        parent_lay.addWidget(w)
        return slider

    def toggle_hue(self):
        self._hue_toggle.setChecked(not self._hue_toggle.isChecked())

    def set_hue_active(self, active: bool):
        self._hue_toggle.setChecked(active)

    def _on_hue_toggle(self, checked: bool):
        self._hue_toggle.setText("ON" if checked else "OFF")
        self._slider_h.setEnabled(checked)
        self._emit()

    def _add_row(self, parent_lay: QVBoxLayout, name: str,
                 track: str, fill: str) -> QSlider:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)

        header = QHBoxLayout()
        header.addWidget(_label(name))
        header.addStretch()
        header.addWidget(self._make_learn_btn(name))
        lay.addLayout(header)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 255)
        slider.setValue(255)
        slider.setStyleSheet(_slider_style(track, fill))
        lay.addWidget(slider)

        parent_lay.addWidget(w)
        return slider

    def _emit(self):
        self.hsv_changed.emit(
            self._hue_toggle.isChecked(),
            float(self._slider_h.value()),
            self._slider_s.value() / 255.0,
            self._slider_v.value() / 255.0,
        )
