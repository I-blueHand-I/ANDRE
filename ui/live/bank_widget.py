from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QGridLayout, QFrame, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap

from ui.theme import BG_MAIN as _BG_BANK
from ui.live.styles import _TOGGLE_BTN, _TARGET_BTN
from ui.live.bank_items import _AnimIcon, _ListRow, _ScanWorker
from engine.constants import SIDE_A, SIDE_B
from ui.shared_styles import _SCROLLBAR_V
from ui.shared_widgets import frame_to_pixmap

_COLS       = 5
_BATCH_SIZE = 8   # widgets added per event-loop tick during populate


class _BankWidget(QWidget):
    load_requested = Signal(object, str)   # (Animation|Video, "A" ou "B")

    def __init__(self, title: str, mode: str = "animation", parent=None):
        super().__init__(parent)
        self._mode               = mode
        self._target             = SIDE_A
        self._last_folder        = ""
        self._preview_anim       = None
        self._preview_idx        = 0
        self._view_mode          = "icon"
        self._cached_animations: list = []   # last successful scan result
        self._pop_gen            = 0         # incremented to cancel in-flight populate

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(4)

        # ── Header ────────────────────────────────────────────────────────────
        header = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "color: #888888; font-family: 'terminal grotesque'; font-weight: bold; font-size: 12px;"
        )
        header.addWidget(title_lbl)
        header.addStretch()

        self._btn_icon_view = QPushButton("⊞")
        self._btn_icon_view.setFixedSize(24, 22)
        self._btn_icon_view.setCheckable(True)
        self._btn_icon_view.setChecked(True)
        self._btn_icon_view.setStyleSheet(_TOGGLE_BTN)
        self._btn_icon_view.clicked.connect(lambda: self._set_view_mode("icon"))

        self._btn_list_view = QPushButton("☰")
        self._btn_list_view.setFixedSize(24, 22)
        self._btn_list_view.setCheckable(True)
        self._btn_list_view.setStyleSheet(_TOGGLE_BTN)
        self._btn_list_view.clicked.connect(lambda: self._set_view_mode("list"))

        self._search_bar = QLineEdit()
        self._search_bar.setPlaceholderText("Search…")
        self._search_bar.setClearButtonEnabled(True)
        self._search_bar.setFixedHeight(22)
        self._search_bar.setStyleSheet("""
            QLineEdit {
                background: #2a2a2a; color: #cccccc;
                border: 1px solid #555; padding: 0 4px;
                font-family: 'terminal grotesque'; font-size: 11px;
            }
            QLineEdit:focus { border-color: #888; }
        """)
        self._search_bar.textChanged.connect(self._apply_filter)

        header.addWidget(self._btn_icon_view)
        header.addWidget(self._btn_list_view)
        header.addWidget(self._search_bar)

        refresh_btn = QPushButton("↺")
        refresh_btn.setFixedSize(24, 22)
        refresh_btn.setStyleSheet("""
            QPushButton { background-color: #3a3a3a; color: white; border: 1px solid #555; font-size: 13px; }
            QPushButton:hover { background-color: #4a4a4a; }
        """)
        refresh_btn.clicked.connect(lambda: self.scan(self._last_folder))
        header.addWidget(refresh_btn)
        lay.addLayout(header)

        # ── Deck target selector ──────────────────────────────────────────────
        target_row = QHBoxLayout()
        target_row.setSpacing(4)
        target_row.setContentsMargins(0, 0, 0, 0)
        self._btn_deck_a = QPushButton("DECK A")
        self._btn_deck_a.setCheckable(True)
        self._btn_deck_a.setChecked(True)
        self._btn_deck_a.setStyleSheet(_TARGET_BTN)
        self._btn_deck_b = QPushButton("DECK B")
        self._btn_deck_b.setCheckable(True)
        self._btn_deck_b.setStyleSheet(_TARGET_BTN)
        self._btn_deck_a.clicked.connect(lambda: self._set_target(SIDE_A))
        self._btn_deck_b.clicked.connect(lambda: self._set_target(SIDE_B))
        target_row.addWidget(self._btn_deck_a)
        target_row.addWidget(self._btn_deck_b)
        target_row.addStretch()
        lay.addLayout(target_row)
        lay.addSpacing(8)

        # ── Zone scrollable ───────────────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background: {_BG_BANK}; }}" + _SCROLLBAR_V
        )
        lay.addWidget(self._scroll, 1)

        # ── Preview strip ─────────────────────────────────────────────────────
        self._preview_strip = QWidget()
        self._preview_strip.setFixedHeight(72)
        self._preview_strip.setStyleSheet(
            "background: #111111; border-top: 1px solid #2a2a2a;"
        )
        ps_lay = QHBoxLayout(self._preview_strip)
        ps_lay.setContentsMargins(6, 4, 6, 4)
        ps_lay.setSpacing(8)

        self._preview_lbl = QLabel()
        self._preview_lbl.setFixedSize(80, 60)
        self._preview_lbl.setAlignment(Qt.AlignCenter)
        self._preview_lbl.setStyleSheet("background: #000000;")
        ps_lay.addWidget(self._preview_lbl)

        self._preview_name = QLabel("— hover to preview —")
        self._preview_name.setStyleSheet(
            "color: #444444; font-family: 'terminal grotesque'; font-size: 10px; background: transparent;"
        )
        ps_lay.addWidget(self._preview_name)
        ps_lay.addStretch()
        lay.addWidget(self._preview_strip)

        # ── Timer preview ─────────────────────────────────────────────────────
        self._timer = QTimer(self)
        self._timer.setInterval(80)
        self._timer.timeout.connect(self._advance_preview)

        self._scan_gen     = 0
        self._scan_workers: set = set()
        self._rebuild_content()
        self._add_placeholder("Configurer un dossier dans SETTINGS")

    # ── Vue ───────────────────────────────────────────────────────────────────

    def _set_view_mode(self, mode: str):
        if mode == self._view_mode:
            return
        self._view_mode = mode
        self._btn_icon_view.setChecked(mode == "icon")
        self._btn_list_view.setChecked(mode == "list")
        self._apply_filter()

    def _rebuild_content(self):
        self._pop_gen += 1   # cancel any in-flight batched populate
        self._on_hover(None)
        old = self._scroll.takeWidget()
        if old:
            old.deleteLater()

        self._content_widget = QWidget()
        self._content_widget.setStyleSheet(f"background: {_BG_BANK};")

        if self._view_mode == "icon":
            self._content_layout = QGridLayout(self._content_widget)
            self._content_layout.setContentsMargins(0, 0, 8, 0)
            self._content_layout.setSpacing(0)
            for c in range(_COLS):
                self._content_layout.setColumnStretch(c, 1)
        else:
            self._content_layout = QVBoxLayout(self._content_widget)
            self._content_layout.setContentsMargins(0, 0, 0, 0)
            self._content_layout.setSpacing(0)
            self._content_layout.setAlignment(Qt.AlignTop)

        self._scroll.setWidget(self._content_widget)

    def _add_placeholder(self, text: str):
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #3a3a3a; font-family: 'terminal grotesque'; font-size: 11px;")
        if isinstance(self._content_layout, QGridLayout):
            self._content_layout.addWidget(lbl, 0, 0, 1, _COLS)
        else:
            self._content_layout.addWidget(lbl)

    def _clear_content(self):
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _populate_widgets_batched(self, animations: list):
        """Add widgets to the layout in small batches, yielding the event loop between each."""
        self._pop_gen += 1
        current_gen = self._pop_gen
        items       = list(animations)
        pos         = [0]
        grid_rc     = [0, 0]   # [row, col] for icon grid

        def _add_batch():
            if current_gen != self._pop_gen:
                return   # superseded by a newer scan or view switch

            end = min(pos[0] + _BATCH_SIZE, len(items))
            for i in range(pos[0], end):
                anim = items[i]
                if self._view_mode == "icon":
                    w = _AnimIcon(anim)
                    w.hovered.connect(self._on_hover)
                    w.load_clicked.connect(
                        lambda a: self.load_requested.emit(a, self._target)
                    )
                    self._content_layout.addWidget(w, grid_rc[0], grid_rc[1])
                    grid_rc[1] += 1
                    if grid_rc[1] >= _COLS:
                        grid_rc[1] = 0
                        grid_rc[0] += 1
                else:
                    w = _ListRow(anim)
                    w.hovered.connect(self._on_hover)
                    w.load_clicked.connect(
                        lambda a: self.load_requested.emit(a, self._target)
                    )
                    self._content_layout.addWidget(w)

            pos[0] = end

            if pos[0] >= len(items):
                # All done — finalise layout
                if self._view_mode == "icon":
                    self._content_layout.setRowStretch(grid_rc[0] + 1, 1)
                else:
                    self._content_layout.addStretch()
            else:
                QTimer.singleShot(0, _add_batch)

        _add_batch()

    # ── Target deck ───────────────────────────────────────────────────────────

    def _set_target(self, deck: str):
        self._target = deck
        self._btn_deck_a.setChecked(deck == SIDE_A)
        self._btn_deck_b.setChecked(deck == SIDE_B)

    # ── Scan (async) ──────────────────────────────────────────────────────────

    def cleanup(self):
        self._timer.stop()
        for worker in list(self._scan_workers):
            worker.quit()
            if not worker.wait(100):
                worker.terminate()

    def scan(self, folder_path: str):
        self._last_folder = folder_path
        self._scan_gen += 1
        gen = self._scan_gen
        self._cached_animations = []   # invalidate cache while new scan runs

        self._rebuild_content()

        folder = Path(folder_path) if folder_path else None
        if not folder or not folder.is_dir():
            msg = ("Configurer un dossier MP4 dans SETTINGS"
                   if self._mode == "video"
                   else "Configurer un dossier dans SETTINGS")
            self._add_placeholder(msg)
            return

        self._add_placeholder("Chargement…")

        worker = _ScanWorker(str(folder), self._mode)
        self._scan_workers.add(worker)
        worker.scan_done.connect(lambda anims: self._on_scan_done(anims, gen))
        worker.finished.connect(lambda: self._scan_workers.discard(worker))
        worker.start()

    def _on_scan_done(self, animations: list, gen: int):
        if gen != self._scan_gen:
            return

        self._cached_animations = animations
        self._apply_filter()

    def _apply_filter(self):
        query = self._search_bar.text().strip().lower()
        filtered = (
            [a for a in self._cached_animations if query in a.name.lower()]
            if query else list(self._cached_animations)
        )
        self._rebuild_content()
        if not filtered:
            msg = "Aucun résultat" if query else (
                "Aucune animation trouvée" if self._mode != "video"
                else "Aucune vidéo trouvée"
            )
            self._add_placeholder(msg)
        else:
            self._populate_widgets_batched(filtered)

    # ── Preview hover ─────────────────────────────────────────────────────────

    def _on_hover(self, animation):
        if animation is None:
            self._timer.stop()
            self._preview_lbl.clear()
            self._preview_name.setText("— hover to preview —")
            self._preview_name.setStyleSheet(
                "color: #444444; font-family: 'terminal grotesque'; font-size: 10px; background: transparent;"
            )
            self._preview_anim = None
            return

        self._preview_anim = animation
        self._preview_idx  = 0
        self._preview_name.setText(animation.name)
        self._preview_name.setStyleSheet(
            "color: #cccccc; font-family: 'terminal grotesque'; font-size: 10px; "
            "font-weight: bold; background: transparent;"
        )
        self._timer.start()

    def _advance_preview(self):
        anim = self._preview_anim
        if anim is None:
            return
        if hasattr(anim, 'get_preview_frame'):
            frame = anim.get_preview_frame(self._preview_idx)
        else:
            frame = anim.get_frame(self._preview_idx)
        self._preview_idx = (self._preview_idx + 1) % anim.frame_count

        px = frame_to_pixmap(frame).scaled(
            self._preview_lbl.size(), Qt.KeepAspectRatio, Qt.FastTransformation
        )
        self._preview_lbl.setPixmap(px)
