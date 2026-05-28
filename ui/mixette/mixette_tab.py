from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QTabWidget,
    QPushButton, QSlider, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, Signal

from ui.theme import BG_DARK as _BG, BG_PANEL, ACCENT, BG_BUTTON
from ui.mixette.styles import _label, _MIDI_BTN
from ui.mixette.main_tools import RGBPanel, HSVPanel
from ui.shared_widgets import ColorDial
from ui.keybind import (
    KeyBindButton, Action, ActionDef,
    COLORS_REGISTRY, GLOBAL_RIGHT_REGISTRY,
    EDIT_LEFT_REGISTRY, EDIT_TOOLS_REGISTRY, EDIT_RIGHT_REGISTRY,
)
from ui.live.styles import _HSLIDER, _STROBE_BTN as _LIVE_STROBE_BTN
from engine.constants import SIDE_A, SIDE_B
from engine.blend_modes import BLEND_MODES

_DECK_PLAY_PAUSE_ACTION = {
    SIDE_A: Action.DECK_A_PLAY_PAUSE,
    SIDE_B: Action.DECK_B_PLAY_PAUSE,
}
_DECK_CUE_ACTION = {
    SIDE_A: Action.DECK_A_CUE,
    SIDE_B: Action.DECK_B_CUE,
}


_TAB_STYLE = f"""
QTabWidget::pane {{
    border: none;
    background-color: {_BG};
}}
QTabBar::tab {{
    background-color: {BG_PANEL};
    color: #777777;
    border: none;
    padding: 10px 22px;
    font-family: 'terminal grotesque', monospace;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: {_BG};
    color: white;
    border-top: 2px solid {ACCENT};
}}
QTabBar::tab:hover:!selected {{
    background-color: {BG_BUTTON};
    color: #aaaaaa;
}}
"""


class MixetteTab(QWidget):
    midi_learn_requested = Signal(str)
    rgb_changed          = Signal(float, float, float)
    hsv_changed          = Signal(bool, float, float, float)
    key_bind_changed     = Signal(str, str)   # action, key_seq

    def __init__(self, config):
        super().__init__()
        self.config = config
        self._active_learn_btn: QPushButton | None = None
        self.setStyleSheet(f"background-color: {_BG};")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(_TAB_STYLE)
        self._tabs.addTab(self._build_colors_tab(),  "COLORS OUTPUT")
        self._tabs.addTab(self._build_global_tab(),  "GLOBAL CONTROLS")
        self._tabs.addTab(self._build_edit_tab_widget(), "EDIT CONTROL")
        self._tabs.addTab(self._build_live_tab(),    "LIVE")
        root.addWidget(self._tabs)

    # ── Tab: COLORS OUTPUT ────────────────────────────────────────────────────

    def _build_colors_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background-color: {_BG};")
        outer = QVBoxLayout(w)
        outer.setContentsMargins(24, 16, 24, 16)
        outer.setSpacing(16)

        self._hsv_panel = HSVPanel()
        self._rgb_panel = RGBPanel()
        self._hsv_panel.hsv_changed.connect(self.hsv_changed)
        self._rgb_panel.rgb_changed.connect(self.rgb_changed)
        self._hsv_panel.midi_learn_requested.connect(self.midi_learn_requested)
        self._rgb_panel.midi_learn_requested.connect(self.midi_learn_requested)

        left_col = QVBoxLayout()
        left_col.setSpacing(12)
        for action_def in COLORS_REGISTRY:
            left_col.addWidget(self._make_key_bind_row(action_def))
        left_col.addWidget(self._hsv_panel, 1)

        panels = QHBoxLayout()
        panels.setSpacing(32)
        panels.addLayout(left_col, 1)
        panels.addWidget(self._rgb_panel, 1)
        outer.addLayout(panels, 1)
        return w

    # ── Tab: GLOBAL CONTROLS ──────────────────────────────────────────────────

    def _build_global_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background-color: {_BG};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(40, 32, 40, 32)
        lay.setSpacing(0)

        cols = QHBoxLayout()
        cols.setSpacing(40)

        left = QVBoxLayout()
        left.setSpacing(16)
        left.addWidget(self._make_strobe_color_row())
        left.addWidget(self._make_strobe_freq_row())
        left.addWidget(self._make_strobe_btn_row())
        left.addStretch()

        right = QVBoxLayout()
        right.setSpacing(16)
        for action_def in GLOBAL_RIGHT_REGISTRY:
            right.addWidget(self._make_key_bind_row(action_def))
        right.addStretch()

        cols.addLayout(left, 1)
        cols.addLayout(right, 1)
        lay.addLayout(cols)
        lay.addStretch()
        return w

    # ── Tab: EDIT CONTROL ─────────────────────────────────────────────────────

    def _build_edit_tab_widget(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background-color: {_BG};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(40, 32, 40, 32)
        lay.setSpacing(12)

        cols = QHBoxLayout()
        cols.setSpacing(40)

        left = QVBoxLayout()
        left.setSpacing(16)
        for action_def in EDIT_LEFT_REGISTRY:
            left.addWidget(self._make_key_bind_row(action_def))
        left.addStretch()

        right = QVBoxLayout()
        right.setSpacing(16)
        for action_def in EDIT_TOOLS_REGISTRY:
            right.addWidget(self._make_key_bind_row(action_def))
        right.addSpacing(8)
        for action_def in EDIT_RIGHT_REGISTRY:
            right.addWidget(self._make_key_bind_row(action_def))
        right.addStretch()

        cols.addLayout(left, 1)
        cols.addLayout(right, 1)
        lay.addLayout(cols)
        lay.addStretch()
        return w

    # ── Tab: LIVE ─────────────────────────────────────────────────────────────

    def _build_live_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background-color: {_BG};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(40, 32, 40, 32)
        lay.setSpacing(24)

        lay.addWidget(_label("LIVE CONTROLS", color="#aaaaaa", size=13))

        decks_row = QHBoxLayout()
        decks_row.setSpacing(60)
        decks_row.addLayout(self._make_deck_section(SIDE_A), 1)
        decks_row.addLayout(self._make_deck_section(SIDE_B), 1)
        lay.addLayout(decks_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #333333; max-height: 1px;")
        lay.addWidget(sep)

        lay.addWidget(self._make_midi_row("CROSSFADER", "CROSSFADER"))
        lay.addStretch()
        return w

    # ── Deck RGB row ──────────────────────────────────────────────────────────

    def _make_deck_rgb_row(self, deck: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(_label("RGB", size=14))
        lay.addStretch()
        for color, channel in (("#cc3333", "RED"), ("#33bb33", "GREEN"), ("#3366cc", "BLUE"), ("#bbbbbb", "SAT")):
            lay.addWidget(_label(channel, color="#666666", size=10), alignment=Qt.AlignVCenter)
            lay.addSpacing(4)
            lay.addWidget(self._make_learn_btn(f"{channel}_{deck}"), alignment=Qt.AlignVCenter)
            lay.addSpacing(12)
        return w

    # ── Strobe rows ───────────────────────────────────────────────────────────

    def _make_strobe_color_row(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(_label("STROBE COLOR", size=14))
        lay.addStretch()
        for color, name in (("#cc3333", "STROBE_R"), ("#33bb33", "STROBE_G"), ("#3366cc", "STROBE_B")):
            dial = ColorDial(color)
            dial.setEnabled(False)
            lay.addWidget(dial, alignment=Qt.AlignVCenter)
            lay.addSpacing(4)
            lay.addWidget(self._make_learn_btn(name), alignment=Qt.AlignVCenter)
            lay.addSpacing(12)
        return w

    def _make_strobe_freq_row(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(_label("STROBE FREQ", size=14))
        lay.addStretch()
        slider = QSlider(Qt.Horizontal)
        slider.setRange(1, 30)
        slider.setValue(5)
        slider.setFixedWidth(120)
        slider.setStyleSheet(_HSLIDER)
        slider.setEnabled(False)
        lay.addWidget(slider, alignment=Qt.AlignVCenter)
        lay.addSpacing(8)
        lay.addWidget(self._make_learn_btn("STROBE_FREQ"), alignment=Qt.AlignVCenter)
        return w

    def _make_strobe_btn_row(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(_label("STROBE", size=14))
        lay.addStretch()
        strobe_btn = QPushButton("STROBE")
        strobe_btn.setFixedWidth(76)
        strobe_btn.setStyleSheet(_LIVE_STROBE_BTN)
        strobe_btn.setEnabled(False)
        lay.addWidget(strobe_btn, alignment=Qt.AlignVCenter)
        lay.addWidget(self._make_learn_btn(Action.STROBE), alignment=Qt.AlignVCenter)
        lay.addWidget(_label("KEY", color="#666666", size=11), alignment=Qt.AlignVCenter)
        kb_btn = KeyBindButton()
        kb_btn.set_key(self.config.get("key_bindings", {}).get(Action.STROBE, ""))
        kb_btn.key_captured.connect(lambda k: self._on_key_bind(Action.STROBE, k))
        lay.addWidget(kb_btn, alignment=Qt.AlignVCenter)
        lay.addWidget(_label("(hold)", color="#555555", size=10), alignment=Qt.AlignVCenter)
        return w

    # ── Key bind row ──────────────────────────────────────────────────────────

    def _make_key_bind_row(self, action_def: ActionDef) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(_label(action_def.label, size=14))
        lay.addStretch()
        lay.addWidget(_label("KEY", color="#666666", size=11), alignment=Qt.AlignVCenter)
        kb_btn = KeyBindButton()
        kb_btn.set_key(self.config.get("key_bindings", {}).get(action_def.name, ""))
        kb_btn.key_captured.connect(lambda k, a=action_def.name: self._on_key_bind(a, k))
        lay.addWidget(kb_btn, alignment=Qt.AlignVCenter)
        if action_def.hold:
            lay.addWidget(_label("(hold)", color="#555555", size=10), alignment=Qt.AlignVCenter)
        return w

    # ── Deck section (LIVE tab) ───────────────────────────────────────────────

    def _make_deck_section(self, deck: str) -> QVBoxLayout:
        lay = QVBoxLayout()
        lay.setSpacing(20)
        lay.addWidget(_label(f"DECK {deck}", color="#aaaaaa", size=13))
        lay.addWidget(self._make_midi_row("FPS",         f"FPS_{deck}"))
        lay.addWidget(self._make_midi_key_row("PLAY/PAUSE", f"PLAY_PAUSE_{deck}", _DECK_PLAY_PAUSE_ACTION[deck]))
        lay.addWidget(self._make_midi_key_row("CUE",        f"CUE_{deck}",        _DECK_CUE_ACTION[deck],        hold=True))

        lay.addSpacing(8)
        lay.addWidget(self._make_deck_rgb_row(deck))

        lay.addSpacing(8)
        lay.addWidget(_label("BLEND MODES", color="#666666", size=11))
        grid = QGridLayout()
        grid.setSpacing(8)
        modes = list(BLEND_MODES.keys())
        for i, mode in enumerate(modes):
            row, col = divmod(i, 2)
            grid.addWidget(self._make_midi_row(mode, f"BLEND_{deck}_{mode}"), row, col)
        lay.addLayout(grid)
        return lay

    def _make_midi_key_row(self, label: str, midi_name: str, action_name: str, hold: bool = False) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(_label(label, size=14))
        lay.addStretch()
        lay.addWidget(self._make_learn_btn(midi_name), alignment=Qt.AlignVCenter)
        lay.addWidget(_label("KEY", color="#666666", size=11), alignment=Qt.AlignVCenter)
        kb_btn = KeyBindButton()
        kb_btn.set_key(self.config.get("key_bindings", {}).get(action_name, ""))
        kb_btn.key_captured.connect(lambda k, a=action_name: self._on_key_bind(a, k))
        lay.addWidget(kb_btn, alignment=Qt.AlignVCenter)
        if hold:
            lay.addWidget(_label("(hold)", color="#555555", size=10), alignment=Qt.AlignVCenter)
        return w

    def _make_midi_row(self, name: str, midi_name: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(_label(name, size=16))
        lay.addStretch()
        lay.addWidget(self._make_learn_btn(midi_name))
        return w

    # ── MIDI learn feedback ───────────────────────────────────────────────────

    def on_learn_bound(self, control_name: str, midi_key: str):
        """Called when MidiManager successfully binds a control. Unchecks the button."""
        if self._active_learn_btn is not None:
            self._active_learn_btn.blockSignals(True)
            self._active_learn_btn.setChecked(False)
            self._active_learn_btn.setText("midi bind")
            self._active_learn_btn.blockSignals(False)
            self._active_learn_btn = None
        self._hsv_panel.on_learn_bound(control_name)
        self._rgb_panel.on_learn_bound(control_name)
        print(f"[MIDI] bound: {control_name} → {midi_key}")

    def _make_learn_btn(self, control_name: str) -> QPushButton:
        """Create a trackable midi bind button."""
        btn = QPushButton("midi bind")
        btn.setCheckable(True)
        btn.setStyleSheet(_MIDI_BTN)
        btn.toggled.connect(lambda checked, n=control_name, b=btn: self._on_learn_toggled(b, checked, n))
        return btn

    def _on_learn_toggled(self, btn: QPushButton, checked: bool, control_name: str):
        if checked:
            if self._active_learn_btn and self._active_learn_btn is not btn:
                self._active_learn_btn.blockSignals(True)
                self._active_learn_btn.setChecked(False)
                self._active_learn_btn.blockSignals(False)
            self._active_learn_btn = btn
            btn.setText("waiting…")
            self.midi_learn_requested.emit(control_name)
        else:
            if self._active_learn_btn is btn:
                self._active_learn_btn = None
            btn.setText("midi bind")
            self.midi_learn_requested.emit("")

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def toggle_hue(self):
        self._hsv_panel.toggle_hue()

    def set_hue_active(self, active: bool):
        self._hsv_panel.set_hue_active(active)

    def _on_key_bind(self, action: str, key_seq: str):
        bindings = dict(self.config.get("key_bindings", {}))
        bindings[action] = key_seq
        self.config.set("key_bindings", bindings)
        self.key_bind_changed.emit(action, key_seq)
