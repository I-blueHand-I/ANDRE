import numpy as np
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QImage

from ui.edit.tools import TOOLS, _ERASE_TOOL, ToolResult


class PixelCanvas(QWidget):
    """
    Canvas interactif pixel art.
    Stocke les pixels comme np.ndarray (H, W, 3) uint8 à la résolution LED.
    Délègue toute la logique de dessin aux outils de tools.py.
    """

    stroke_will_start = Signal()               # émis au mousePress, avant tout dessin
    frame_changed     = Signal(object)         # np.ndarray (H, W, 3) — émis après chaque modification
    color_picked      = Signal(int, int, int)  # r, g, b — émis par l'eyedropper

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config         = config
        self._tool          = "brush"
        self._color         = (255, 255, 255)
        self._thickness     = 1
        self._pixels: np.ndarray | None = None
        self._drawing       = False
        self._onion_enabled = False
        self._onion_frame:  np.ndarray | None = None

        self.setMouseTracking(False)
        self.setMinimumSize(280, 200)
        self.setStyleSheet("background-color: #111111;")
        self.setCursor(Qt.CrossCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self._init_frame()

    # ── API publique ──────────────────────────────────────────────────────────

    def set_tool(self, name: str):
        self._tool = name
        self.setCursor(Qt.PointingHandCursor if name == "eyedropper" else Qt.CrossCursor)

    def set_color(self, r: int, g: int, b: int):
        self._color = (r, g, b)

    def set_thickness(self, t: int):
        self._thickness = max(1, int(t))

    def set_onion_enabled(self, v: bool):
        self._onion_enabled = v
        self.update()

    def set_onion_frame(self, arr: np.ndarray | None):
        self._onion_frame = arr
        self.update()

    def on_frame_selected(self, _i: int, arr: np.ndarray, prev: np.ndarray | None = None):
        W, H = self._resolution()
        if arr.shape == (H, W, 3):
            self._pixels = arr.copy()
        self._onion_frame = prev
        self.update()

    def set_frame(self, arr: np.ndarray):
        W, H = self._resolution()
        if arr.shape == (H, W, 3):
            self._pixels = arr.copy()
            self.update()

    def reset_resolution(self):
        self._init_frame()
        self.update()

    # ── Interne ───────────────────────────────────────────────────────────────

    def _resolution(self) -> tuple[int, int]:
        res = self.config.get("led_resolution", [21, 16])
        return int(res[0]), int(res[1])

    def _init_frame(self):
        W, H = self._resolution()
        self._pixels = np.zeros((H, W, 3), dtype=np.uint8)

    def _screen_to_pixel(self, pos) -> tuple[int, int] | None:
        W, H = self._resolution()
        col = int(pos.x() * W / max(self.width(),  1))
        row = int(pos.y() * H / max(self.height(), 1))
        if 0 <= col < W and 0 <= row < H:
            return col, row
        return None

    def _apply(self, pos, is_press: bool, right_button: bool):
        px = self._screen_to_pixel(pos)
        if px is None or self._pixels is None:
            return
        col, row = px
        tool = _ERASE_TOOL if right_button else TOOLS.get(self._tool)
        if tool is None:
            return

        result: ToolResult = (
            tool.press(self._pixels, col, row, self._color, self._thickness)
            if is_press else
            tool.drag(self._pixels, col, row, self._color, self._thickness)
        )

        if result.modified:
            self.update()
            self.frame_changed.emit(self._pixels.copy())
        if result.picked_color is not None:
            r, g, b = result.picked_color
            self._color = (r, g, b)
            self.color_picked.emit(r, g, b)

    # ── Événements souris ─────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        right = event.button() == Qt.RightButton
        if event.button() in (Qt.LeftButton, Qt.RightButton):
            self.stroke_will_start.emit()
            self._drawing = True
            self._apply(event.position().toPoint(), is_press=True, right_button=right)

    def mouseMoveEvent(self, event):
        if not self._drawing:
            return
        right = bool(event.buttons() & Qt.RightButton)
        left  = bool(event.buttons() & Qt.LeftButton)
        if left or right:
            self._apply(event.position().toPoint(), is_press=False, right_button=right)

    def mouseReleaseEvent(self, event):
        self._drawing = False

    # ── Rendu ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        if self._pixels is None:
            return
        W, H = self._resolution()
        w, h = self.width(), self.height()
        cw = w / W
        ch = h / H

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing,          False)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)

        painter.fillRect(0, 0, w, h, QColor("#111111"))

        # ── Onion skin (dessiné avant la frame courante) ──────────────────────
        if self._onion_enabled and self._onion_frame is not None:
            onion = self._onion_frame
            lit   = onion.any(axis=2)
            if lit.any():
                tinted = np.zeros((H, W, 4), dtype=np.uint8)
                tinted[lit, 0] = np.minimum(255, onion[lit, 0].astype(np.int16) + 80)
                tinted[lit, 1] = (onion[lit, 1].astype(np.float32) * 0.25).astype(np.uint8)
                tinted[lit, 2] = (onion[lit, 2].astype(np.float32) * 0.25).astype(np.uint8)
                tinted[lit, 3] = 160
                tc = np.ascontiguousarray(tinted)
                painter.drawImage(QRect(0, 0, w, h),
                                  QImage(tc.data, W, H, W * 4, QImage.Format_RGBA8888))

        # ── Frame courante (pixels noirs transparents si onion actif) ─────────
        arr = np.ascontiguousarray(self._pixels)
        if self._onion_enabled and self._onion_frame is not None:
            curr_rgba = np.zeros((H, W, 4), dtype=np.uint8)
            lit_curr  = arr.any(axis=2)
            curr_rgba[lit_curr, :3] = arr[lit_curr]
            curr_rgba[lit_curr, 3]  = 255
            cc = np.ascontiguousarray(curr_rgba)
            img = QImage(cc.data, W, H, W * 4, QImage.Format_RGBA8888)
        else:
            img = QImage(arr.data, W, H, W * 3, QImage.Format_RGB888)
        painter.drawImage(QRect(0, 0, w, h), img)

        # ── Grille ────────────────────────────────────────────────────────────
        pen = QPen(QColor("#2e2e2e"))
        pen.setWidth(1)
        painter.setPen(pen)
        for x in range(W + 1):
            painter.drawLine(round(x * cw), 0, round(x * cw), h)
        for y in range(H + 1):
            painter.drawLine(0, round(y * ch), w, round(y * ch))
