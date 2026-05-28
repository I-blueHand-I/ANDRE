from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QLabel
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut

from ui.config_dialog import ConfigDialog

import numpy as np
from engine.edit_animation import EditAnimation
from ui.edit.edit_tab import EditTab
from ui.theme import TAB_ACTIVE, TAB_INACTIVE, TAB_HOVER, TAB_BORDER, BG_MAIN
from ui.live.live_tab import LiveTab
from ui.mixette.mixette_tab import MixetteTab
from ui.output_window import OutputWindow
from ui.keybind import KeyBindManager, Action
from engine.render_engine import RenderEngine
from engine.blend_modes import BLEND_MODES
from output.udp_output import UDPOutput
from midi.midi_manager import MidiManager
from engine.constants import SIDE_A, SIDE_B



def _midi_range(v: float, lo: int, hi: int) -> int:
    """Map a normalised MIDI value (0.0–1.0) to an integer in [lo, hi]."""
    return max(lo, min(hi, round(v * (hi - lo) + lo)))


_TAB_STYLE = f"""
QPushButton {{{{
    background-color: {{bg}};
    color: {{fg}};
    border: none;
    outline: none;
    font-family: 'terminal grotesque', monospace;
    font-size: 14px;
    font-weight: bold;
    letter-spacing: 2px;
    padding: 10px 0;
}}}}
QPushButton:hover {{{{
    background-color: {TAB_HOVER};
    border: none;
    outline: none;
}}}}
"""


class _TabButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self._set_active(False)

    def _set_active(self, active: bool):
        bg = TAB_BORDER   if active else TAB_INACTIVE
        fg = "#000000"    if active else "#ffffff"
        self.setStyleSheet(_TAB_STYLE.format(bg=bg, fg=fg))

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._set_active(checked)


class MainWindow(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setWindowTitle("SendPix3")
        self.resize(1280, 820)
        self.setMinimumSize(1024, 700)
        self.setStyleSheet(f"QMainWindow {{ background-color: {BG_MAIN}; }}")

        central = QWidget()
        central.setStyleSheet(f"background-color: {BG_MAIN};")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Tab bar
        self._tab_buttons: list[_TabButton] = []
        root.addWidget(self._build_tab_bar())

        # Stacked content
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background-color: {BG_MAIN};")
        root.addWidget(self.stack, 1)

        # Engine + output (créés avant LiveTab qui en a besoin)
        self.render_engine = RenderEngine(config)
        self.udp_output    = UDPOutput(config)
        self.output_window = OutputWindow(config)

        # Tabs
        self.edit_tab    = EditTab(config)
        self.live_tab    = LiveTab(config, self.render_engine)
        self.mixette_tab = MixetteTab(config)
        self.stack.addWidget(self.edit_tab)     # 0
        self.stack.addWidget(self.live_tab)     # 1
        self.stack.addWidget(self.mixette_tab)  # 2

        # Wire signals — DirectConnection bypasses main-thread event loop entirely
        self.render_engine.frame_ready.connect(self.udp_output.enqueue_frame, Qt.DirectConnection)
        self.render_engine.frame_ready.connect(self.output_window.set_frame,   Qt.DirectConnection)
        self.output_window.broadcast_changed.connect(self.udp_output.set_broadcasting)
        self.output_window.broadcast_changed.connect(
            lambda _: self.render_engine.refresh_resolution()
        )

        # Mixette → moteur
        self.mixette_tab.rgb_changed.connect(self.render_engine.set_rgb)
        self.mixette_tab.hsv_changed.connect(self.render_engine.set_hsv)

        # Edit live
        self.edit_tab.live_edit_deck_changed.connect(self._on_edit_live_deck)
        self.live_tab.animation_loaded.connect(self.edit_tab.stop_deck_blink)

        # Live tab → main window (remplace les self.window() dans live_tab)
        self.live_tab.interp_changed.connect(self.output_window.set_interpolation)
        self.live_tab.output_requested.connect(self._open_output)
        self.live_tab.settings_requested.connect(self.open_settings)
        self.edit_tab.settings_requested.connect(self.open_settings)

        # Keyboard shortcuts (global)
        self._setup_shortcuts()

        # Doit être appelé en dernier — dépend de edit_tab, mixette_tab, render_engine
        self._setup_keybinds()

        # MIDI state (shadow values so per-channel updates don't clobber other channels)
        self._midi_rgb    = [1.0, 1.0, 1.0]
        self._midi_hsv    = [False, 0.0, 1.0, 1.0]
        self._midi_strobe = [0, 0, 0]

        # Keep MIDI shadow in sync with GUI-driven changes
        self.mixette_tab.rgb_changed.connect(
            lambda r, g, b: self._midi_rgb.__setitem__(slice(None), [r, g, b])
        )
        self.mixette_tab.hsv_changed.connect(
            lambda h, hd, s, v: self._midi_hsv.__setitem__(slice(None), [h, hd, s, v])
        )

        self._setup_midi_callbacks()

        self.midi_manager = MidiManager(config)
        self.mixette_tab.midi_learn_requested.connect(self.midi_manager.start_learn)
        self.midi_manager.midi_value.connect(self._on_midi_value)
        self.midi_manager.learn_bound.connect(self.mixette_tab.on_learn_bound)
        device = config.get("midi_device", "")
        if device:
            self.midi_manager.open_device(device)

        # Start threads
        self.render_engine.start()
        self.udp_output.start()
        self.midi_manager.start()

        # Initialise les deux decks avec une frame noire pour symétriser le layout dès le départ
        res = self.config.get("led_resolution", [21, 16])
        _black = [np.zeros((int(res[1]), int(res[0]), 3), dtype=np.uint8)]
        self.render_engine.deck_a.load(EditAnimation(lambda: _black))
        self.render_engine.deck_b.load(EditAnimation(lambda: _black))

        # Show output window
        self.output_window.show()

        # Synchro initiale des contrôles Live → moteur + output window
        self.output_window.set_interpolation(self.live_tab.interp_combo.currentText())

        # Scan initial des banks
        self.live_tab.refresh_banks()

        self._set_tab(0)
        QTimer.singleShot(0, self._first_launch_settings)

    # ── Edit live ─────────────────────────────────────────────────────────────

    def _on_edit_live_deck(self, side: str, active: bool):
        deck = self.render_engine.deck_a if side == SIDE_A else self.render_engine.deck_b
        if active:
            deck.load(EditAnimation(self.edit_tab.timeline.get_frames))
            self.live_tab.set_deck_fps(side, self.edit_tab.fps_slider.value())
        else:
            deck.unload()

    # ── Settings dialog ───────────────────────────────────────────────────────

    def _run_settings_dialog(self, force_resolution: bool = False) -> None:
        old_res = list(self.config.get("led_resolution", [21, 16]))
        dlg = ConfigDialog(self.config, self)
        dlg.exec()
        self.live_tab.refresh_banks()
        new_res = list(self.config.get("led_resolution", [21, 16]))
        if new_res != old_res or force_resolution:
            self.edit_tab.on_resolution_changed()
            self.render_engine.refresh_resolution()
        self.midi_manager.open_device(self.config.get("midi_device", ""))

    def _first_launch_settings(self):
        self._run_settings_dialog(force_resolution=True)

    def open_settings(self):
        self._run_settings_dialog()

    def _open_output(self):
        self.output_window.show()
        self.output_window.raise_()
        self.output_window.activateWindow()

    # ── MIDI dispatch ─────────────────────────────────────────────────────────

    def _setup_midi_callbacks(self):
        re  = self.render_engine
        lt  = self.live_tab

        def _set_rgb(ch, v):
            self._midi_rgb[ch] = v
            re.set_rgb(*self._midi_rgb)

        def _set_hsv(idx, scale, v):
            self._midi_hsv[idx] = v * scale
            re.set_hsv(*self._midi_hsv)

        def _set_strobe(ch, v):
            self._midi_strobe[ch] = int(v * 255)
            re.set_strobe_color(*self._midi_strobe)

        self._midi_callbacks: dict[str, object] = {
            "RED":         lambda v: _set_rgb(0, v),
            "GREEN":       lambda v: _set_rgb(1, v),
            "BLUE":        lambda v: _set_rgb(2, v),
            "HUE":         lambda v: (_set_hsv(1, 360.0, v), self.mixette_tab._hsv_panel._slider_h.setValue(int(v * 360))),
            "SATURATION":  lambda v: (_set_hsv(2, 1.0, v), self.mixette_tab._hsv_panel._slider_s.setValue(int(v * 255))),
            "VALUE":       lambda v: (_set_hsv(3, 1.0, v), self.mixette_tab._hsv_panel._slider_v.setValue(int(v * 255))),
            "STROBE_R":    lambda v: (_set_strobe(0, v), lt._strobe_r.setValue(int(v * 255))),
            "STROBE_G":    lambda v: (_set_strobe(1, v), lt._strobe_g.setValue(int(v * 255))),
            "STROBE_B":    lambda v: (_set_strobe(2, v), lt._strobe_b.setValue(int(v * 255))),
            "STROBE_FREQ": lambda v: (re.set_strobe_freq(_midi_range(v, 1, 30)), lt._strobe_freq_slider.setValue(_midi_range(v, 1, 30))),
            "STROBE":      lambda v: lt.set_strobe_active(v > 0.5),
            "CROSSFADER":  lambda v: lt.crossfader.setValue(_midi_range(v, 0, 100)),
            "FPS_A":          lambda v: lt.set_deck_fps(SIDE_A, _midi_range(v, 1, 60)),
            "FPS_B":          lambda v: lt.set_deck_fps(SIDE_B, _midi_range(v, 1, 60)),
            "PLAY_PAUSE_A":   lambda v: lt.toggle_deck_pause(SIDE_A) if v > 0.5 else None,
            "PLAY_PAUSE_B":   lambda v: lt.toggle_deck_pause(SIDE_B) if v > 0.5 else None,
            "CUE_A":          lambda v: lt.set_cue_active(SIDE_A, v > 0.5),
            "CUE_B":          lambda v: lt.set_cue_active(SIDE_B, v > 0.5),
            "TOGGLE_HUE":  lambda v: self.mixette_tab.set_hue_active(v > 0.5),
            "RED_A":   lambda v: (lt._deck_r_a.setValue(int(v * 255)),),
            "GREEN_A": lambda v: (lt._deck_g_a.setValue(int(v * 255)),),
            "BLUE_A":  lambda v: (lt._deck_b_a.setValue(int(v * 255)),),
            "SAT_A":   lambda v: (lt._deck_sat_a.setValue(int(v * 255)),),
            "RED_B":   lambda v: (lt._deck_r_b.setValue(int(v * 255)),),
            "GREEN_B": lambda v: (lt._deck_g_b.setValue(int(v * 255)),),
            "BLUE_B":  lambda v: (lt._deck_b_b.setValue(int(v * 255)),),
            "SAT_B":   lambda v: (lt._deck_sat_b.setValue(int(v * 255)),),
        }

        for mode in BLEND_MODES:
            self._midi_callbacks[f"BLEND_A_{mode}"] = (
                lambda v, m=mode: lt.blend_combo_a.setCurrentText(m) if v > 0.5 else None
            )
            self._midi_callbacks[f"BLEND_B_{mode}"] = (
                lambda v, m=mode: lt.blend_combo_b.setCurrentText(m) if v > 0.5 else None
            )

    def _on_midi_value(self, control: str, value: float):
        cb = self._midi_callbacks.get(control)
        if cb:
            cb(value)

    def _setup_keybinds(self):
        self._keybind_manager = KeyBindManager(self)

        callbacks = {
            Action.OUTPUT:            self._open_output,
            Action.SETTINGS:          self.open_settings,
            Action.TOGGLE_HUE:        self.mixette_tab.toggle_hue,
            Action.LIVE_EDIT_A:       lambda: self.edit_tab.toggle_live_edit_deck(SIDE_A),
            Action.LIVE_EDIT_B:       lambda: self.edit_tab.toggle_live_edit_deck(SIDE_B),
            Action.DECK_A_PLAY_PAUSE: lambda: self.live_tab.toggle_deck_pause(SIDE_A),
            Action.DECK_B_PLAY_PAUSE: lambda: self.live_tab.toggle_deck_pause(SIDE_B),
            Action.ADD_FRAME:         self.edit_tab.add_frame,
            Action.ADD_4_FRAMES:      lambda: self.edit_tab.add_frames(4),
            Action.ADD_12_FRAMES:     lambda: self.edit_tab.add_frames(12),
            Action.ADD_24_FRAMES:     lambda: self.edit_tab.add_frames(24),
            Action.NEW_ANIM:          self.edit_tab.new_anim,
            Action.PLAY_PAUSE:        self.edit_tab.play_pause,
            Action.NEXT_FRAME:        self.edit_tab.go_next,
            Action.NEXT_FRAME_2:      self.edit_tab.play_forward,
            Action.PREV_FRAME:        self.edit_tab.go_prev,
            Action.PREV_FRAME_2:      self.edit_tab.play_backward,
            Action.EXPORT_ANIM:       self.edit_tab.trigger_export,
            Action.TOOL_BRUSH:        lambda: self.edit_tab._set_tool("brush"),
            Action.TOOL_FILL:         lambda: self.edit_tab._set_tool("fill"),
            Action.TOOL_EYEDROPPER:   lambda: self.edit_tab._set_tool("eyedropper"),
        }
        for action, cb in callbacks.items():
            self._keybind_manager.register(action, cb)

        # Hold actions: key/MIDI down = on, key/MIDI up = off
        self._keybind_manager.register_hold(
            Action.TOOL_ONION,
            lambda: self.edit_tab.set_onion_active(True),
            lambda: self.edit_tab.set_onion_active(False),
        )
        self._keybind_manager.register_hold(
            Action.STROBE,
            lambda: self.live_tab.set_strobe_active(True),
            lambda: self.live_tab.set_strobe_active(False),
        )
        self._keybind_manager.register_hold(
            Action.DECK_A_CUE,
            lambda: self.live_tab.set_cue_active(SIDE_A, True),
            lambda: self.live_tab.set_cue_active(SIDE_A, False),
        )
        self._keybind_manager.register_hold(
            Action.DECK_B_CUE,
            lambda: self.live_tab.set_cue_active(SIDE_B, True),
            lambda: self.live_tab.set_cue_active(SIDE_B, False),
        )

        _defaults = {
            Action.TOOL_BRUSH: "B",
            Action.TOOL_FILL: "G",
            Action.TOOL_EYEDROPPER: "I",
            Action.TOOL_ONION: "O",
        }
        user_bindings = self.config.get("key_bindings", {})
        for action, key in _defaults.items():
            if action not in user_bindings:
                user_bindings[action] = key
        self.config.set("key_bindings", user_bindings)
        for action, key in user_bindings.items():
            self._keybind_manager.update_binding(action, key)
        self.mixette_tab.key_bind_changed.connect(self._keybind_manager.update_binding)

    # ── Tab bar ───────────────────────────────────────────────────────────────

    def _build_tab_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(48)
        bar.setStyleSheet(f"background-color: {TAB_INACTIVE};")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        for i, name in enumerate(["EDIT", "LIVE", "MIXETTE"]):
            btn = _TabButton(name)
            btn.clicked.connect(lambda _, idx=i: self._set_tab(idx))
            lay.addWidget(btn, 1)
            self._tab_buttons.append(btn)

        return bar

    def _set_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self._tab_buttons):
            btn.setChecked(i == index)

    # ── Shortcuts ─────────────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+1"), self).activated.connect(lambda: self._set_tab(0))
        QShortcut(QKeySequence("Ctrl+2"), self).activated.connect(lambda: self._set_tab(1))
        QShortcut(QKeySequence("Ctrl+3"), self).activated.connect(lambda: self._set_tab(2))
        QShortcut(QKeySequence(Qt.Key_Tab), self).activated.connect(self._cycle_tab)

    def _cycle_tab(self):
        self._set_tab((self.stack.currentIndex() + 1) % self.stack.count())

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self.live_tab.cleanup()
        self.render_engine.stop()
        self.udp_output.stop()
        self.midi_manager.stop()
        self.render_engine.wait(2000)
        self.udp_output.wait(2000)
        self.midi_manager.wait(1000)
        self.output_window.close()
        self.config.save()
        event.accept()
