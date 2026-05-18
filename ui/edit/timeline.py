import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QScrollArea
from PySide6.QtCore import Qt, Signal, QTimer

from ui.edit.frame_thumb import _FrameThumb, _AddFrameThumb
from ui.shared_styles import _SCROLLBAR_V


class Timeline(QWidget):
    """
    Panneau timeline : liste de frames miniatures dans un scroll 2 colonnes.
    Émet frame_selected(index, current_arr, prev_arr_or_None) à chaque sélection.
    Émet reset() avant de vider l'animation (permet à l'hôte d'arrêter la lecture).
    """

    frame_selected    = Signal(int, object, object)  # index, current_arr, prev_arr_or_None
    reset             = Signal()
    state_will_change = Signal()              # émis avant toute mutation structurelle

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config    = config
        self._frames:  list[np.ndarray] = []
        self._thumbs:  list[_FrameThumb] = []
        self._current: int = 0
        self._build_ui()
        self._add_first_frame()

    # ── Résolution ────────────────────────────────────────────────────────────

    def _get_resolution(self) -> tuple[int, int]:
        res = self.config.get("led_resolution", [21, 16])
        return int(res[0]), int(res[1])

    # ── Construction UI ───────────────────────────────────────────────────────

    def _build_ui(self):
        self.setFixedWidth(200)
        self.setStyleSheet("background-color: #252525; border-right: 1px solid #333;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }"
                             + _SCROLLBAR_V)
        self._scroll = scroll

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        self._grid = QGridLayout(inner)
        self._grid.setContentsMargins(0, 0, 10, 0)
        self._grid.setSpacing(8)
        self._grid.setColumnStretch(0, 1)
        self._grid.setColumnStretch(1, 1)
        self._grid.setRowStretch(999, 1)

        self._add_btn = _AddFrameThumb(self.add_frame)
        scroll.setWidget(inner)
        lay.addWidget(scroll, 1)

    def _add_first_frame(self):
        W, H  = self._get_resolution()
        blank = np.zeros((H, W, 3), dtype=np.uint8)
        self._frames.append(blank)
        thumb = _FrameThumb(0, blank, selected=True)
        thumb.clicked.connect(self.select)
        thumb.delete_requested.connect(self.delete_frame)
        self._grid.addWidget(thumb, 0, 0)
        self._thumbs.append(thumb)
        self._refresh_add_btn()

    def _refresh_add_btn(self):
        self._grid.addWidget(self._add_btn, *divmod(len(self._frames), 2))

    # ── API publique ──────────────────────────────────────────────────────────

    @property
    def current_index(self) -> int:
        return self._current

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    def get_frames(self) -> list[np.ndarray]:
        return self._frames

    def add_n_frames(self, n: int):
        self.state_will_change.emit()
        W, H = self._get_resolution()
        for _ in range(n):
            blank = np.zeros((H, W, 3), dtype=np.uint8)
            self._frames.append(blank)
            i = len(self._frames) - 1
            thumb = _FrameThumb(i, blank)
            thumb.clicked.connect(self.select)
            thumb.delete_requested.connect(self.delete_frame)
            self._grid.addWidget(thumb, *divmod(i, 2))
            self._thumbs.append(thumb)
        self._refresh_add_btn()
        self.select(len(self._frames) - 1)
        QTimer.singleShot(30, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def add_frame(self, arr: np.ndarray | None = None):
        if arr is None:   # ajout manuel via "+" — les appels programmatiques gèrent l'historique eux-mêmes
            self.state_will_change.emit()
            W, H  = self._get_resolution()
            blank = np.zeros((H, W, 3), dtype=np.uint8)
        else:
            blank = arr.copy()
        self._frames.append(blank)
        i     = len(self._frames) - 1
        thumb = _FrameThumb(i, blank)
        thumb.clicked.connect(self.select)
        thumb.delete_requested.connect(self.delete_frame)
        self._grid.addWidget(thumb, *divmod(i, 2))
        self._thumbs.append(thumb)
        self._refresh_add_btn()
        self.select(i)
        QTimer.singleShot(30, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def delete_frame(self, i: int):
        if len(self._frames) <= 1:
            return
        self.state_will_change.emit()
        self._grid.removeWidget(self._thumbs[i])
        self._thumbs[i].setParent(None)
        del self._frames[i]
        del self._thumbs[i]

        self._grid.removeWidget(self._add_btn)
        for j, t in enumerate(self._thumbs):
            self._grid.removeWidget(t)
            t.index = j
            self._grid.addWidget(t, *divmod(j, 2))

        self._refresh_add_btn()
        self.select(min(i, len(self._frames) - 1))

    def new_anim(self):
        self.state_will_change.emit()
        self.reset.emit()
        self._grid.removeWidget(self._add_btn)
        for thumb in self._thumbs:
            self._grid.removeWidget(thumb)
            thumb.setParent(None)
        self._frames.clear()
        self._thumbs.clear()
        self._current = 0
        self._add_first_frame()
        self.frame_selected.emit(0, self._frames[0], None)

    def select(self, i: int):
        if not (0 <= i < len(self._frames)):
            return
        self._current = i
        for j, t in enumerate(self._thumbs):
            t.set_selected(j == i)
        prev = self._frames[i - 1] if i > 0 else None
        self.frame_selected.emit(i, self._frames[i], prev)

    def restore_state(self, frames: list[np.ndarray], current: int) -> np.ndarray:
        """Restaure un état complet sans émettre de signaux. Retourne la frame courante."""
        self._grid.removeWidget(self._add_btn)
        for t in self._thumbs:
            self._grid.removeWidget(t)
            t.setParent(None)

        self._frames = [f.copy() for f in frames]
        self._thumbs = []
        self._current = min(current, len(self._frames) - 1)

        for i, frame in enumerate(self._frames):
            thumb = _FrameThumb(i, frame, selected=(i == self._current))
            thumb.clicked.connect(self.select)
            thumb.delete_requested.connect(self.delete_frame)
            self._grid.addWidget(thumb, *divmod(i, 2))
            self._thumbs.append(thumb)

        self._refresh_add_btn()
        return self._frames[self._current]

    def update_current_frame(self, arr: np.ndarray):
        self._frames[self._current] = arr
        self._thumbs[self._current].set_pixels(arr)
