from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QSlider, QComboBox, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

from ui.theme import BG_PANEL as _BG_MAIN, BG_BUTTON as _BG_CTRL, BG_MAIN as _BG_BANK
from engine.blend_modes import BLEND_MODES
from engine.constants import SIDE_A, SIDE_B
from ui.shared_styles import _btn
from ui.live.styles import _VSLIDER, _COMBO, _HSLIDER, _STROBE_BTN, _TOGGLE_BTN, _CUE_BTN
from ui.live.deck_preview import DeckPreview, _FpsRuler
from ui.live.bank_widget import _BankWidget
from ui.live.crossfader import _CrossfaderSlider
from ui.shared_widgets import ColorDial as _ColorDial


class LiveTab(QWidget):
    animation_loaded   = Signal(str)
    interp_changed     = Signal(str)
    output_requested   = Signal()
    settings_requested = Signal()

    def __init__(self, config, render_engine=None):
        super().__init__()
        self.config = config
        self._render_engine = render_engine
        self.setStyleSheet(f"background-color: {_BG_MAIN};")
        self._build_ui()
        if render_engine is not None:
            self._wire_controls()

    # ── Construction UI ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        decks_row = QHBoxLayout()
        decks_row.setContentsMargins(0, 0, 0, 0)
        decks_row.setSpacing(0)
        decks_row.addWidget(self._build_deck(SIDE_A), 1)
        decks_row.addWidget(self._build_deck(SIDE_B), 1)
        decks_widget = QWidget()
        decks_widget.setLayout(decks_row)
        root.addWidget(decks_widget, 3)

        root.addWidget(self._build_blend_bar())    # blend modes + crossfader
        root.addWidget(self._build_strobe_bar())   # strobe + interp + output/settings
        root.addWidget(self._build_banks(), 2)

    # ── Deck ──────────────────────────────────────────────────────────────────

    def _build_deck(self, side: str) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background-color: {_BG_MAIN};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)

        fps_col = self._build_fps_column(side)
        preview = DeckPreview(side)

        if side == SIDE_A:
            self._preview_a = preview
            lay.addWidget(fps_col)
            lay.addWidget(preview, 1)
        else:
            self._preview_b = preview
            lay.addWidget(preview, 1)
            lay.addWidget(fps_col)

        return w

    def _build_fps_column(self, deck_side: str) -> QWidget:
        w = QWidget()
        w.setFixedWidth(76)
        w.setStyleSheet("background-color: #4a4a4a;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(2)

        plus = QLabel("+")
        plus.setAlignment(Qt.AlignHCenter)
        plus.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        lay.addWidget(plus)

        slider_row = QHBoxLayout()
        slider_row.setContentsMargins(0, 0, 0, 0)
        slider_row.setSpacing(0)

        slider = QSlider(Qt.Vertical)
        slider.setRange(1, 60)
        slider.setValue(15)
        slider.setStyleSheet(_VSLIDER)
        slider.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        slider.setFixedWidth(22)

        if deck_side == SIDE_A:
            self._fps_slider_a = slider
        else:
            self._fps_slider_b = slider

        ruler = _FpsRuler()
        ruler.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        slider_row.addWidget(slider, alignment=Qt.AlignHCenter)
        slider_row.addWidget(ruler)
        lay.addLayout(slider_row, 1)

        val = QLabel("15")
        val.setAlignment(Qt.AlignHCenter)
        val.setStyleSheet(
            "color: #cc2222; font-family: 'terminal grotesque'; font-weight: bold; font-size: 14px;"
        )
        slider.valueChanged.connect(lambda v: val.setText(str(v)))
        lay.addWidget(val)

        fps_lbl = QLabel("FPS")
        fps_lbl.setAlignment(Qt.AlignHCenter)
        fps_lbl.setStyleSheet(
            "color: white; font-family: 'terminal grotesque'; font-size: 9px; font-weight: bold;"
        )
        lay.addWidget(fps_lbl)

        return w

    # ── Barre blend modes + crossfader ────────────────────────────────────────

    def _build_blend_bar(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(52)
        w.setStyleSheet("background-color: #3e3e3e;")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(0)

        _lbl = "color: white; font-family: 'terminal grotesque'; font-weight: bold; font-size: 13px; min-width: 16px;"
        _pct = "color: #aaaaaa; font-family: 'terminal grotesque'; font-size: 11px; min-width: 34px;"

        left = QHBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(6)
        self.blend_combo_a = QComboBox()
        self.blend_combo_a.addItems(list(BLEND_MODES.keys()))
        self.blend_combo_a.setStyleSheet(_COMBO)
        left.addWidget(self.blend_combo_a, alignment=Qt.AlignVCenter)

        self._pause_btn_a = QPushButton("⏸")
        self._pause_btn_a.setCheckable(True)
        self._pause_btn_a.setChecked(True)
        self._pause_btn_a.setFixedSize(32, 28)
        self._pause_btn_a.setStyleSheet(_TOGGLE_BTN)
        self._pause_btn_a.toggled.connect(
            lambda c: self._pause_btn_a.setText("⏸" if c else "▶")
        )
        left.addWidget(self._pause_btn_a, alignment=Qt.AlignVCenter)

        self._cue_btn_a = QPushButton("CUE")
        self._cue_btn_a.setFixedSize(40, 28)
        self._cue_btn_a.setStyleSheet(_CUE_BTN)
        left.addWidget(self._cue_btn_a, alignment=Qt.AlignVCenter)

        left.addStretch()

        center = QHBoxLayout()
        center.setContentsMargins(0, 0, 0, 0)
        center.setSpacing(6)
        a_lbl = QLabel("A")
        a_lbl.setStyleSheet(_lbl)
        center.addWidget(a_lbl)
        self.pct_a = QLabel("50%")
        self.pct_a.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.pct_a.setStyleSheet(_pct)
        center.addWidget(self.pct_a)
        self.crossfader = _CrossfaderSlider()
        self.crossfader.setFixedWidth(180)
        center.addWidget(self.crossfader)
        self.pct_b = QLabel("50%")
        self.pct_b.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.pct_b.setStyleSheet(_pct)
        center.addWidget(self.pct_b)
        b_lbl = QLabel("B")
        b_lbl.setStyleSheet(_lbl)
        center.addWidget(b_lbl)
        self.crossfader.valueChanged.connect(
            lambda v: (self.pct_a.setText(f"{100 - v}%"), self.pct_b.setText(f"{v}%"))
        )

        right = QHBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(6)
        right.addStretch()

        self._cue_btn_b = QPushButton("CUE")
        self._cue_btn_b.setFixedSize(40, 28)
        self._cue_btn_b.setStyleSheet(_CUE_BTN)
        right.addWidget(self._cue_btn_b, alignment=Qt.AlignVCenter)

        self._pause_btn_b = QPushButton("⏸")
        self._pause_btn_b.setCheckable(True)
        self._pause_btn_b.setChecked(True)
        self._pause_btn_b.setFixedSize(32, 28)
        self._pause_btn_b.setStyleSheet(_TOGGLE_BTN)
        self._pause_btn_b.toggled.connect(
            lambda c: self._pause_btn_b.setText("⏸" if c else "▶")
        )
        right.addWidget(self._pause_btn_b, alignment=Qt.AlignVCenter)

        self.blend_combo_b = QComboBox()
        self.blend_combo_b.addItems(list(BLEND_MODES.keys()))
        self.blend_combo_b.setStyleSheet(_COMBO)
        right.addWidget(self.blend_combo_b, alignment=Qt.AlignVCenter)

        lay.addLayout(left, 1)
        lay.addLayout(center, 0)
        lay.addLayout(right, 1)

        return w

    # ── Barre strobe + contrôles ──────────────────────────────────────────────

    def _build_strobe_bar(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(56)
        w.setStyleSheet(f"background-color: {_BG_CTRL};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(0)

        # ── Strobe (gauche) ───────────────────────────────────────────────────
        left = QHBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(6)

        self._strobe_r = _ColorDial("#cc3333")
        self._strobe_g = _ColorDial("#33bb33")
        self._strobe_b = _ColorDial("#3366cc")
        left.addWidget(self._strobe_r, alignment=Qt.AlignVCenter)
        left.addWidget(self._strobe_g, alignment=Qt.AlignVCenter)
        left.addWidget(self._strobe_b, alignment=Qt.AlignVCenter)

        left.addSpacing(8)

        self._strobe_freq_slider = QSlider(Qt.Horizontal)
        self._strobe_freq_slider.setRange(1, 30)
        self._strobe_freq_slider.setValue(5)
        self._strobe_freq_slider.setFixedWidth(110)
        self._strobe_freq_slider.setStyleSheet(_HSLIDER)
        left.addWidget(self._strobe_freq_slider, alignment=Qt.AlignVCenter)

        left.addSpacing(6)

        self._strobe_btn = QPushButton("STROBE")
        self._strobe_btn.setFixedWidth(76)
        self._strobe_btn.setStyleSheet(_STROBE_BTN)
        left.addWidget(self._strobe_btn, alignment=Qt.AlignVCenter)

        left.addSpacing(6)

        self.strobe_blend_combo = QComboBox()
        self.strobe_blend_combo.addItems(list(BLEND_MODES.keys()))
        self.strobe_blend_combo.setStyleSheet(_COMBO)
        left.addWidget(self.strobe_blend_combo, alignment=Qt.AlignVCenter)

        left.addStretch()

        # ── Contrôles (droite) ────────────────────────────────────────────────
        right = QHBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(8)

        self.interp_combo = QComboBox()
        self.interp_combo.addItems(["NEAREST", "BICUBIC", "AREA", "LINEAR"])
        self.interp_combo.setCurrentText("AREA")
        self.interp_combo.setStyleSheet(_COMBO)
        right.addWidget(self.interp_combo, alignment=Qt.AlignVCenter)

        output_btn = _btn("OUTPUT", bg="#3a3a3a", border="#666666", size=11,
                          pad="4px 10px", hover="#4a4a4a")
        output_btn.clicked.connect(self._open_output)
        right.addWidget(output_btn, alignment=Qt.AlignVCenter)

        settings_btn = _btn("SETTINGS", bg="#3a3a3a", border="#666666", size=11,
                             pad="4px 10px", hover="#4a4a4a")
        settings_btn.clicked.connect(self._open_settings)
        right.addWidget(settings_btn, alignment=Qt.AlignVCenter)

        lay.addLayout(left, 1)
        lay.addLayout(right, 0)

        return w

    # ── Banks ─────────────────────────────────────────────────────────────────

    def _build_banks(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background-color: {_BG_BANK};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._bank_anim  = _BankWidget("ANIMATIONS BANK", mode="animation")
        lay.addWidget(self._bank_anim, 1)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #3a3a3a;")
        lay.addWidget(sep)

        self._bank_video = _BankWidget("MP4 BANK", mode="video")
        lay.addWidget(self._bank_video, 1)
        return w

    # ── Câblage moteur ────────────────────────────────────────────────────────

    def _wire_controls(self):
        re = self._render_engine

        self._fps_slider_a.valueChanged.connect(re.deck_a.set_fps)
        self._fps_slider_b.valueChanged.connect(re.deck_b.set_fps)
        re.deck_a.set_fps(self._fps_slider_a.value())
        re.deck_b.set_fps(self._fps_slider_b.value())

        self.interp_combo.currentTextChanged.connect(re.set_interpolation)
        self.interp_combo.currentTextChanged.connect(self._on_interp_changed)
        re.set_interpolation(self.interp_combo.currentText())

        self.blend_combo_a.currentTextChanged.connect(lambda m: re.set_blend_mode(SIDE_A, m))
        self.blend_combo_b.currentTextChanged.connect(lambda m: re.set_blend_mode(SIDE_B, m))

        self._pause_btn_a.toggled.connect(re.deck_a.set_paused)
        self._pause_btn_b.toggled.connect(re.deck_b.set_paused)
        
        self._cue_btn_a.pressed.connect(lambda: self._pause_btn_a.setChecked(True))
        self._cue_btn_a.pressed.connect(re.deck_a.cue_start)
        self._cue_btn_a.released.connect(re.deck_a.cue_end)
        self._cue_btn_b.pressed.connect(lambda: self._pause_btn_b.setChecked(True))
        self._cue_btn_b.pressed.connect(re.deck_b.cue_start)
        self._cue_btn_b.released.connect(re.deck_b.cue_end)

        self.crossfader.valueChanged.connect(lambda v: re.set_crossfader(v / 100.0))

        re.deck_a_ready.connect(self._preview_a.update_frame)
        re.deck_b_ready.connect(self._preview_b.update_frame)

        self._strobe_btn.pressed.connect(lambda: re.set_strobe_active(True))
        self._strobe_btn.released.connect(lambda: re.set_strobe_active(False))
        self._strobe_freq_slider.valueChanged.connect(re.set_strobe_freq)
        self._strobe_r.valueChanged.connect(self._emit_strobe_color)
        self._strobe_g.valueChanged.connect(self._emit_strobe_color)
        self._strobe_b.valueChanged.connect(self._emit_strobe_color)
        self.strobe_blend_combo.currentTextChanged.connect(re.set_strobe_blend_mode)

        self._bank_anim.load_requested.connect(self._on_load_requested)
        self._bank_video.load_requested.connect(self._on_load_requested)

    def _emit_strobe_color(self):
        self._render_engine.set_strobe_color(
            self._strobe_r.value(),
            self._strobe_g.value(),
            self._strobe_b.value(),
        )

    def _on_load_requested(self, animation, deck_side: str):
        deck = self._render_engine.deck_a if deck_side == SIDE_A else self._render_engine.deck_b
        deck.load(animation)
        self.animation_loaded.emit(deck_side)

    def set_deck_fps(self, side: str, fps: int):
        slider = self._fps_slider_a if side == SIDE_A else self._fps_slider_b
        slider.setValue(fps)

    def refresh_banks(self):
        self._bank_anim.scan(self.config.get("animations_folder", ""))
        self._bank_video.scan(self.config.get("mp4_folder", ""))

    def toggle_deck_pause(self, side: str) -> None:
        btn = self._pause_btn_a if side == SIDE_A else self._pause_btn_b
        btn.toggle()

    def set_cue_active(self, side: str, active: bool) -> None:
        cue_btn  = self._cue_btn_a  if side == SIDE_A else self._cue_btn_b
        pause_btn = self._pause_btn_a if side == SIDE_A else self._pause_btn_b
        deck = self._render_engine.deck_a if side == SIDE_A else self._render_engine.deck_b
        cue_btn.setDown(active)
        if active:
            pause_btn.setChecked(True)
            deck.cue_start()
        else:
            deck.cue_end()

    def set_strobe_active(self, active: bool):
        self._strobe_btn.setDown(active)
        self._render_engine.set_strobe_active(active)

    def cleanup(self):
        self._bank_anim.cleanup()
        self._bank_video.cleanup()

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_interp_changed(self, mode: str):
        self.interp_changed.emit(mode)

    def _open_output(self):
        self.output_requested.emit()

    def _open_settings(self):
        self.settings_requested.emit()
