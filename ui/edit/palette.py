import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor

_MAX_PALETTE  = 24
_INITIAL_SIZE = 12
_COLS         = 6
_SWATCH       = 24    # px par slot
_GAP          = 2     # px entre slots (fond visible = séparateur naturel)
_BORDER       = 2     # épaisseur du highlight de sélection
_BG           = QColor("#111111")
_EMPTY        = QColor("#2a2a2a")
_PLUS_BG      = QColor("#1e1e1e")
_PLUS_MARK    = QColor("#555555")
_EMPTY_MARK   = QColor("#4a4a4a")
_ACCENT       = QColor("#e0156b")


class ColorPalette(QWidget):
    """
    Palette de couleurs expandable (12 → 24 slots).
    Clic gauche slot rempli  → sélectionne la couleur.
    Clic gauche slot vide    → stocke la couleur active, sélectionne.
    Clic droit               → stocke la couleur active, sélectionne.
    Clic "+"                 → ajoute un slot avec la couleur active, sélectionne.
    Slot sélectionné + changement de couleur active → slot mis à jour en temps réel.
    """

    color_selected = Signal(int, int, int)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config        = config
        self._active       = (255, 255, 255)
        self._selected_idx: int | None = None
        self._colors: list[tuple[int, int, int] | None] = []

        self.setCursor(Qt.PointingHandCursor)
        self._load()
        self._update_geometry()

    # ── API publique ──────────────────────────────────────────────────────────

    def set_active_color(self, r: int, g: int, b: int):
        self._active = (r, g, b)
        if self._selected_idx is not None:
            self._colors[self._selected_idx] = (r, g, b)
            self._save()
            self.update()

    # ── Géométrie ─────────────────────────────────────────────────────────────

    def _cell_count(self) -> int:
        return len(self._colors) + (1 if len(self._colors) < _MAX_PALETTE else 0)

    def _update_geometry(self):
        rows = max(1, math.ceil(self._cell_count() / _COLS))
        w = _COLS * _SWATCH + (_COLS - 1) * _GAP
        h = rows  * _SWATCH + (rows  - 1) * _GAP
        self.setFixedSize(w, h)

    # ── Persistance ───────────────────────────────────────────────────────────

    def _load(self):
        saved = self.config.get("palette", [])
        if not saved:
            self._colors = [None] * _INITIAL_SIZE
            return
        self._colors = []
        for val in saved[:_MAX_PALETTE]:
            if isinstance(val, str) and val.startswith("#"):
                c = QColor(val)
                self._colors.append((c.red(), c.green(), c.blue()) if c.isValid() else None)
            else:
                self._colors.append(None)
        if not self._colors:
            self._colors = [None] * _INITIAL_SIZE

    def _save(self):
        self.config.set("palette", [
            "#{:02X}{:02X}{:02X}".format(*c) if c else None
            for c in self._colors
        ])

    # ── Hit-test ──────────────────────────────────────────────────────────────

    def _pos_to_cell(self, pos) -> int | None:
        step = _SWATCH + _GAP
        col  = pos.x() // step
        row  = pos.y() // step
        if col >= _COLS:
            return None
        if pos.x() - col * step >= _SWATCH:
            return None   # dans la gouttière horizontale
        if pos.y() - row * step >= _SWATCH:
            return None   # dans la gouttière verticale
        idx = row * _COLS + col
        return idx if 0 <= idx < self._cell_count() else None

    # ── Événements ────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        cell = self._pos_to_cell(event.position().toPoint())
        if cell is None:
            return

        n = len(self._colors)

        # Cellule "+" → ajoute un slot avec la couleur active
        if cell == n:
            self._colors.append(self._active)
            self._selected_idx = cell
            self._save()
            self._update_geometry()
            self.update()
            return

        if event.button() == Qt.LeftButton:
            if self._colors[cell] is not None:
                self._selected_idx = cell
                self.color_selected.emit(*self._colors[cell])
                self.update()
            else:
                self._store(cell)

        elif event.button() == Qt.RightButton:
            self._store(cell)

    def _store(self, idx: int):
        self._colors[idx] = self._active
        self._selected_idx = idx
        self._save()
        self.update()

    # ── Rendu (100 % fillRect — pixel-perfect) ────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        # Fond = couleur des gouttières
        painter.fillRect(self.rect(), _BG)

        step = _SWATCH + _GAP
        n    = len(self._colors)

        for cell in range(self._cell_count()):
            col = cell % _COLS
            row = cell // _COLS
            x   = col * step
            y   = row * step

            # ── Cellule "+" ───────────────────────────────────────────────────
            if cell == n:
                painter.fillRect(x, y, _SWATCH, _SWATCH, _PLUS_BG)
                self._draw_plus(painter, x, y, _PLUS_MARK)
                continue

            # ── Slot vide ─────────────────────────────────────────────────────
            c = self._colors[cell]
            if c is None:
                painter.fillRect(x, y, _SWATCH, _SWATCH, _EMPTY)
                self._draw_plus(painter, x, y, _EMPTY_MARK)
            else:
                painter.fillRect(x, y, _SWATCH, _SWATCH, QColor(*c))

            # ── Highlight sélection ───────────────────────────────────────────
            if cell == self._selected_idx:
                b = _BORDER
                S = _SWATCH
                painter.fillRect(x,         y,         S, b,     _ACCENT)  # haut
                painter.fillRect(x,         y + S - b, S, b,     _ACCENT)  # bas
                painter.fillRect(x,         y + b,     b, S-2*b, _ACCENT)  # gauche
                painter.fillRect(x + S - b, y + b,     b, S-2*b, _ACCENT)  # droite

    @staticmethod
    def _draw_plus(painter: QPainter, x: int, y: int, color: QColor):
        mx = x + _SWATCH // 2
        my = y + _SWATCH // 2
        painter.fillRect(mx - 4, my - 1, 9, 2, color)
        painter.fillRect(mx - 1, my - 4, 2, 9, color)
