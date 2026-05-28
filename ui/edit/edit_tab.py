import numpy as np
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QSlider, QSizePolicy, QColorDialog
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor

from ui.edit.canvas import PixelCanvas
from ui.edit.colorwheel import ColorPicker
from ui.edit.palette import ColorPalette
from ui.edit.timeline import Timeline
from ui.edit.export_widget import ExportWidget
from ui.edit.history import History
from ui.shared_styles import _btn, _BTN
from ui.theme import ACCENT, DECK_A, DECK_A_HOVER, DECK_A_BRIGHT, DECK_B, DECK_B_HOVER, DECK_B_BRIGHT, BORDER
from engine.constants import SIDE_A, SIDE_B


class EditTab(QWidget):
    live_edit_deck_changed = Signal(str, bool)  # (side "A"/"B", active)
    settings_requested     = Signal()

    def __init__(self, config):
        super().__init__()
        self.config        = config
        self.setStyleSheet("background-color: #1e1e1e;")
        self._active_color = (255, 255, 255)
        self._tool_btns:   list[QPushButton] = []
        self._playing:     bool  = False
        self._play_direction: int = 1
        self._clipboard:   np.ndarray | None = None
        self._history      = History(20)
        self._play_timer   = QTimer(self)
        self._play_timer.timeout.connect(self._tick_playback)
        self._live_active: set[str] = set()
        self._blink_on:    bool = False
        self._blink_timer  = QTimer(self)
        self._blink_timer.setInterval(600)
        self._blink_timer.timeout.connect(self._blink_tick)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Zone principale
        main = QHBoxLayout()
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        self.timeline = Timeline(self.config)
        main.addWidget(self.timeline)
        main.addWidget(self._build_canvas_area(), 1)
        main.addWidget(self._build_tools())

        root.addLayout(main, 1)
        root.addWidget(self._build_bottom_bar())

        self.canvas.frame_changed.connect(self.timeline.update_current_frame)
        self.canvas.stroke_will_start.connect(self._push_history)
        self.timeline.frame_selected.connect(self.canvas.on_frame_selected)
        self.timeline.state_will_change.connect(self._push_history)
        self.timeline.reset.connect(self._stop_playback)

    # ── Canvas (sans contrôles de lecture) ───────────────────────────────────

    def _build_canvas_area(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background-color: #1e1e1e;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        fps_row = QHBoxLayout()
        fps_lbl = QLabel("FPS")
        fps_lbl.setStyleSheet(
            "color: white; font-family: 'terminal grotesque'; font-weight: bold; font-size: 12px;"
        )
        fps_row.addWidget(fps_lbl)

        self.fps_slider = QSlider(Qt.Horizontal)
        self.fps_slider.setRange(1, 60)
        self.fps_slider.setValue(12)
        self.fps_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{ background: #333; height: 4px; border-radius: 2px; }}
            QSlider::handle:horizontal {{
                background: {ACCENT}; width: 10px; height: 16px;
                margin: -6px 0; border-radius: 0;
            }}
            QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
        """)
        fps_row.addWidget(self.fps_slider, 1)

        self.fps_val_lbl = QLabel("12")
        self.fps_val_lbl.setStyleSheet(
            "color: #cc2222; font-family: 'terminal grotesque'; font-weight: bold; min-width: 24px;"
        )
        self.fps_slider.valueChanged.connect(self._on_fps_changed)
        fps_row.addWidget(self.fps_val_lbl)

        fps_max = QLabel("60")
        fps_max.setStyleSheet("color: #888; font-family: 'terminal grotesque'; font-size: 11px;")
        fps_row.addWidget(fps_max)
        lay.addLayout(fps_row)

        self.canvas = PixelCanvas(self.config)
        self.canvas.color_picked.connect(self._on_color_picked)
        lay.addWidget(self.canvas, 1)

        return w

    # ── Tools (sans section live/export) ─────────────────────────────────────

    def _build_tools(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(172)
        w.setStyleSheet("background-color: #252525; border-left: 1px solid #333;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        tools_row = QHBoxLayout()
        tools_row.setSpacing(4)
        for name, tool_id, tip in [("B", "brush",      "Brush"),
                                    ("G", "fill",       "Fill"),
                                    ("I", "eyedropper", "Eyedropper")]:
            b = _btn(name, size=14, pad="6px 10px", checkable=True)
            b.setToolTip(tip)
            b.setFixedSize(44, 34)
            b.clicked.connect(lambda _, t=tool_id: self._set_tool(t))
            tools_row.addWidget(b)
            self._tool_btns.append(b)

        self._tool_btns[0].setChecked(True)
        lay.addLayout(tools_row)

        onion_btn = _btn("ONION", size=11, pad="4px 8px")
        onion_btn.setStyleSheet(
            onion_btn.styleSheet()
            + f"QPushButton:pressed {{ background-color: {ACCENT}; border-color: #ff4499; }}"
        )
        onion_btn.setToolTip("Onion skin — maintenir O")
        onion_btn.pressed.connect(lambda: self.canvas.set_onion_enabled(True))
        onion_btn.released.connect(lambda: self.canvas.set_onion_enabled(False))
        self._onion_btn = onion_btn
        lay.addWidget(onion_btn)

        thick_lbl = QLabel("THICK")
        thick_lbl.setStyleSheet(
            "color: #aaa; font-family: 'terminal grotesque'; font-size: 10px; font-weight: bold;"
        )
        lay.addWidget(thick_lbl)

        thick_row = QHBoxLayout()
        self.thick_slider = QSlider(Qt.Horizontal)
        self.thick_slider.setRange(1, 5)
        self.thick_slider.setValue(1)
        self.thick_slider.setStyleSheet("""
            QSlider::groove:horizontal { background: #444; height: 4px; border-radius: 2px; }
            QSlider::handle:horizontal {
                background: white; width: 12px; height: 12px;
                margin: -4px 0; border-radius: 6px;
            }
        """)
        t1 = QLabel("1")
        t1.setStyleSheet("color: #888; font-family: 'terminal grotesque'; font-size: 10px;")
        t5 = QLabel("5")
        t5.setStyleSheet("color: #888; font-family: 'terminal grotesque'; font-size: 10px;")
        thick_row.addWidget(t1)
        thick_row.addWidget(self.thick_slider, 1)
        thick_row.addWidget(t5)
        lay.addLayout(thick_row)
        self.thick_slider.valueChanged.connect(self.canvas.set_thickness)

        color_lbl = QLabel("COLOR")
        color_lbl.setStyleSheet(
            "color: #aaa; font-family: 'terminal grotesque'; font-size: 10px; font-weight: bold;"
        )
        lay.addWidget(color_lbl)

        self._color_swatch = QPushButton()
        self._color_swatch.setFixedHeight(28)
        self._color_swatch.setToolTip("Choisir une couleur")
        self._color_swatch.clicked.connect(self._open_color_dialog)
        self._update_swatch(*self._active_color)
        lay.addWidget(self._color_swatch)

        self.color_picker = ColorPicker()
        self.color_picker.color_changed.connect(self._apply_color)
        lay.addWidget(self.color_picker, alignment=Qt.AlignHCenter)

        self.palette = ColorPalette(self.config)
        self.palette.color_selected.connect(self._apply_color)
        lay.addWidget(self.palette, alignment=Qt.AlignHCenter)

        lay.addStretch()

        settings_btn = _btn("SETTINGS", size=10, pad="4px 8px")
        settings_btn.clicked.connect(self._open_settings)
        lay.addWidget(settings_btn)

        return w

    # ── Barre du bas unifiée ──────────────────────────────────────────────────

    def _build_bottom_bar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet("background: #1a1a1a; border-top: 1px solid #333;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Colonne gauche — largeur timeline
        left = QWidget()
        left.setFixedWidth(200)
        left.setStyleSheet("border-right: 1px solid #333;")
        l_lay = QVBoxLayout(left)
        l_lay.setContentsMargins(8, 6, 8, 6)
        l_lay.setSpacing(4)

        add_row = QHBoxLayout()
        add_row.setSpacing(4)
        for n in (4, 12, 24):
            b = _btn(f"+{n}", size=10, pad="3px 4px")
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.clicked.connect(lambda _, count=n: self.timeline.add_n_frames(count))
            add_row.addWidget(b)
        l_lay.addLayout(add_row)

        new_btn = _btn("NEW ANIM", size=11, pad="6px")
        new_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        new_btn.clicked.connect(self.timeline.new_anim)
        l_lay.addWidget(new_btn, 1)

        lay.addWidget(left)

        # Colonne centrale — contrôles de lecture
        center = QWidget()
        c_lay = QHBoxLayout(center)
        c_lay.setContentsMargins(8, 6, 8, 6)
        c_lay.setSpacing(4)

        _bs = """
            QPushButton {{
                background-color: #2e2e2e; color: white;
                border: 1px solid #555; font-size: {size}px;
            }}
            QPushButton:hover {{ background-color: #3e3e3e; }}
        """
        def _mk(icon, tip, w=50, size=20):
            b = QPushButton(icon)
            b.setToolTip(tip)
            b.setFixedWidth(w)
            b.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
            b.setStyleSheet(_bs.format(size=size))
            return b

        self._play_bwd_btn = _mk("◀◀", "Play backward")
        btn_prev           = _mk("◀",  "Previous frame")
        self._play_btn     = _mk("▶",  "Play / Pause", w=68)
        btn_next           = _mk("▶|", "Next frame")
        self._play_fwd_btn = _mk("▶▶", "Play forward")

        self._play_bwd_btn.clicked.connect(self._play_backward)
        btn_prev.clicked.connect(self._go_prev)
        self._play_btn.clicked.connect(self._play_pause)
        btn_next.clicked.connect(self._go_next)
        self._play_fwd_btn.clicked.connect(self._play_forward)

        c_lay.addWidget(self._play_bwd_btn)
        c_lay.addWidget(btn_prev)
        c_lay.addStretch()
        c_lay.addWidget(self._play_btn)
        c_lay.addStretch()
        c_lay.addWidget(btn_next)
        c_lay.addWidget(self._play_fwd_btn)
        lay.addWidget(center, 1)

        # Colonne droite — live edit + export (largeur tools)
        right = QWidget()
        right.setFixedWidth(172)
        right.setStyleSheet("border-left: 1px solid #333;")
        r_lay = QVBoxLayout(right)
        r_lay.setContentsMargins(8, 6, 8, 6)
        r_lay.setSpacing(4)

        live_row = QHBoxLayout()
        live_row.setSpacing(4)
        da = _btn("DECK A", bg="#881111", hover="#aa2222", size=11, pad="6px 4px")
        db = _btn("DECK B", bg="#116611", hover="#228822", size=11, pad="6px 4px")
        da.clicked.connect(lambda: self._on_deck_btn_clicked(SIDE_A))
        db.clicked.connect(lambda: self._on_deck_btn_clicked(SIDE_B))
        self._da = da
        self._db = db
        self._da_style_dim    = _BTN.format(bg=DECK_A,       fg="white", border=BORDER,
                                            size=11, pad="6px 4px", hover=DECK_A_HOVER)
        self._da_style_bright = _BTN.format(bg=DECK_A_BRIGHT, fg="white", border=DECK_A_BRIGHT,
                                            size=11, pad="6px 4px", hover=DECK_A_BRIGHT)
        self._db_style_dim    = _BTN.format(bg=DECK_B,       fg="white", border=BORDER,
                                            size=11, pad="6px 4px", hover=DECK_B_HOVER)
        self._db_style_bright = _BTN.format(bg=DECK_B_BRIGHT, fg="white", border=DECK_B_BRIGHT,
                                            size=11, pad="6px 4px", hover=DECK_B_BRIGHT)
        live_row.addWidget(da)
        live_row.addWidget(db)
        r_lay.addLayout(live_row)
        self._export_widget = ExportWidget(self.config, self.timeline.get_frames)
        r_lay.addWidget(self._export_widget)

        lay.addWidget(right)
        return bar

    # ── Playback ──────────────────────────────────────────────────────────────

    def _on_fps_changed(self, v: int):
        self.fps_val_lbl.setText(str(v))
        if self._playing:
            self._play_timer.setInterval(1000 // v)

    def _play_forward(self):
        if self._playing and self._play_direction == 1:
            self._stop_playback()
        else:
            self._play_direction = 1
            if not self._playing:
                self._play_timer.start(1000 // self.fps_slider.value())
                self._playing = True
            self._update_play_btns()

    def _play_backward(self):
        if self._playing and self._play_direction == -1:
            self._stop_playback()
        else:
            self._play_direction = -1
            if not self._playing:
                self._play_timer.start(1000 // self.fps_slider.value())
                self._playing = True
            self._update_play_btns()

    def _play_pause(self):
        self._play_forward()

    def _stop_playback(self):
        if self._playing:
            self._play_timer.stop()
            self._playing = False
        self._update_play_btns()

    def _update_play_btns(self):
        self._play_btn.setText("⏸" if self._playing and self._play_direction == 1 else "▶")
        self._play_bwd_btn.setText("⏸" if self._playing and self._play_direction == -1 else "◀◀")

    def _tick_playback(self):
        self.timeline.select(
            (self.timeline.current_index + self._play_direction) % self.timeline.frame_count
        )

    def _go_prev(self): self.timeline.select(max(0, self.timeline.current_index - 1))
    def _go_next(self): self.timeline.select(min(self.timeline.frame_count - 1,
                                                  self.timeline.current_index + 1))

    # ── Color / Tool ──────────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        self.canvas.setFocus()

    def keyPressEvent(self, event):
        mods = event.modifiers()
        key  = event.key()
        if mods == Qt.ControlModifier:
            if key == Qt.Key_C:
                self._clipboard = self.timeline.get_frames()[self.timeline.current_index].copy()
            elif key == Qt.Key_V and self._clipboard is not None:
                self._push_history()
                if self.timeline.current_index == self.timeline.frame_count - 1:
                    self.timeline.add_frame(self._clipboard)
                else:
                    self.timeline.update_current_frame(self._clipboard.copy())
                    self.canvas.set_frame(self._clipboard)
            elif key == Qt.Key_Z:
                self._undo()
            elif key == Qt.Key_Y:
                self._redo()
        elif mods == (Qt.ControlModifier | Qt.ShiftModifier) and key == Qt.Key_Z:
            self._redo()
        elif mods == Qt.NoModifier:
            if key == Qt.Key_O and not event.isAutoRepeat():
                self._onion_btn.setDown(True)
                self.canvas.set_onion_enabled(True)
            elif key == Qt.Key_B:
                self._set_tool("brush")
            elif key == Qt.Key_G:
                self._set_tool("fill")
            elif key == Qt.Key_I:
                self._set_tool("eyedropper")
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_O and not event.isAutoRepeat():
            self._onion_btn.setDown(False)
            self.canvas.set_onion_enabled(False)
        super().keyReleaseEvent(event)

    def _push_history(self):
        self._history.push(self.timeline.get_frames(), self.timeline.current_index)

    def _undo(self):
        state = self._history.undo(self.timeline.get_frames(), self.timeline.current_index)
        if state:
            frames, current = state
            arr = self.timeline.restore_state(frames, current)
            prev = frames[current - 1] if current > 0 else None
            self.canvas.on_frame_selected(current, arr, prev)

    def _redo(self):
        state = self._history.redo(self.timeline.get_frames(), self.timeline.current_index)
        if state:
            frames, current = state
            arr = self.timeline.restore_state(frames, current)
            prev = frames[current - 1] if current > 0 else None
            self.canvas.on_frame_selected(current, arr, prev)

    def _set_tool(self, tool_id: str):
        self.canvas.set_tool(tool_id)
        tool_ids = ["brush", "fill", "eyedropper"]
        for btn, tid in zip(self._tool_btns, tool_ids):
            btn.setChecked(tid == tool_id)

    def _open_color_dialog(self):
        initial = QColor(*self._active_color)
        color = QColorDialog.getColor(initial, self, "Couleur active")
        if color.isValid():
            self._apply_color(color.red(), color.green(), color.blue())

    def _on_color_picked(self, r: int, g: int, b: int):
        self._apply_color(r, g, b)
        self._set_tool("brush")

    def _apply_color(self, r: int, g: int, b: int):
        self._active_color = (r, g, b)
        self.canvas.set_color(r, g, b)
        self._update_swatch(r, g, b)
        self.color_picker.set_color(r, g, b)
        self.palette.set_active_color(r, g, b)

    def _update_swatch(self, r: int, g: int, b: int):
        fg = "#000000" if (r * 299 + g * 587 + b * 114) > 128000 else "#ffffff"
        self._color_swatch.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); border: 1px solid #666; color: {fg}; "
            f"font-family: 'terminal grotesque'; font-size: 9px;"
        )
        self._color_swatch.setText(f"#{r:02X}{g:02X}{b:02X}")

    def on_resolution_changed(self):
        self._history = History(20)
        self.canvas.reset_resolution()
        self.timeline.new_anim()

    def _open_settings(self):
        self.settings_requested.emit()

    # ── Live edit deck ────────────────────────────────────────────────────────

    def add_frame(self):
        self.timeline.add_frame()

    def add_frames(self, count: int):
        self.timeline.add_n_frames(count)

    def new_anim(self):
        self.timeline.new_anim()

    def play_pause(self):
        self._play_pause()

    def play_forward(self):
        self._play_forward()

    def play_backward(self):
        self._play_backward()

    def go_next(self):
        self._go_next()

    def go_prev(self):
        self._go_prev()

    def trigger_export(self):
        self._export_widget.trigger()

    def toggle_live_edit_deck(self, side: str):
        self._on_deck_btn_clicked(side)

    def _on_deck_btn_clicked(self, side: str):
        if side in self._live_active:
            self.stop_deck_blink(side)
            self.live_edit_deck_changed.emit(side, False)
        else:
            self.start_deck_blink(side)
            self.live_edit_deck_changed.emit(side, True)

    def start_deck_blink(self, side: str):
        self._live_active.add(side)
        if not self._blink_timer.isActive():
            self._blink_on = True
            self._blink_timer.start()
        self._blink_update()

    def stop_deck_blink(self, side: str):
        self._live_active.discard(side)
        if not self._live_active:
            self._blink_timer.stop()
        self._blink_update()

    def _blink_tick(self):
        self._blink_on = not self._blink_on
        self._blink_update()

    def _blink_update(self):
        if SIDE_A in self._live_active:
            self._da.setStyleSheet(self._da_style_bright if self._blink_on else self._da_style_dim)
        else:
            self._da.setStyleSheet(self._da_style_dim)
        if SIDE_B in self._live_active:
            self._db.setStyleSheet(self._db_style_bright if self._blink_on else self._db_style_dim)
        else:
            self._db.setStyleSheet(self._db_style_dim)
