import math
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QPainter, QColor, QPen,
    QConicalGradient, QRadialGradient, QLinearGradient
)


class ColorWheel(QWidget):
    """
    Disque teinte + saturation interactif.
    Angle depuis le centre = teinte (hue), distance du centre = saturation.
    """

    hs_changed = Signal(float, float)   # hue (0–1), saturation (0–1)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 140)
        self.setCursor(Qt.CrossCursor)
        self._hue = 0.0
        self._sat = 0.0

    def set_hs(self, hue: float, sat: float):
        self._hue = max(0.0, hue)
        self._sat = max(0.0, min(1.0, sat))
        self.update()

    # ── Interne ───────────────────────────────────────────────────────────────

    def _params(self) -> tuple[int, int, int]:
        r  = min(self.width(), self.height()) // 2 - 4
        cx = self.width()  // 2
        cy = self.height() // 2
        return cx, cy, r

    def _pos_to_hs(self, pos) -> tuple[float, float] | None:
        cx, cy, r = self._params()
        dx = pos.x() - cx
        dy = pos.y() - cy
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > r:
            return None
        h = (math.atan2(-dy, dx) / (2 * math.pi)) % 1.0
        s = dist / r
        return h, s

    # ── Événements ────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            hs = self._pos_to_hs(event.position().toPoint())
            if hs:
                self._hue, self._sat = hs
                self.update()
                self.hs_changed.emit(*hs)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            hs = self._pos_to_hs(event.position().toPoint())
            if hs:
                self._hue, self._sat = hs
                self.update()
                self.hs_changed.emit(*hs)

    # ── Rendu ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        cx, cy, r = self._params()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)

        # Dégradé conique — teintes
        cg = QConicalGradient(cx, cy, 0)
        for i in range(13):
            cg.setColorAt(i / 12.0, QColor.fromHsvF((i % 12) / 12.0, 1.0, 1.0))
        painter.setBrush(cg)
        painter.drawEllipse(cx - r, cy - r, 2 * r, 2 * r)

        # Dégradé radial — saturation (blanc au centre = désaturé)
        rg = QRadialGradient(cx, cy, r)
        rg.setColorAt(0.0, QColor(255, 255, 255, 220))
        rg.setColorAt(0.6, QColor(255, 255, 255,  60))
        rg.setColorAt(1.0, QColor(255, 255, 255,   0))
        painter.setBrush(rg)
        painter.drawEllipse(cx - r, cy - r, 2 * r, 2 * r)

        # Curseur à la position teinte/saturation courante
        angle = self._hue * 2 * math.pi
        dist  = self._sat * r
        cur_x = int(cx + dist * math.cos(angle))
        cur_y = int(cy - dist * math.sin(angle))

        pen = QPen(QColor(0, 0, 0, 180))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(cur_x - 5, cur_y - 5, 10, 10)

        pen.setColor(QColor(255, 255, 255, 220))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawEllipse(cur_x - 4, cur_y - 4, 8, 8)


class _ValueSlider(QWidget):
    """Slider horizontal de luminosité : noir à gauche, couleur pleine à droite."""

    value_changed = Signal(float)   # 0.0 – 1.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(16)
        self.setCursor(Qt.SizeHorCursor)
        self._value = 1.0
        self._hue   = 0.0
        self._sat   = 0.0

    def set_color_params(self, hue: float, sat: float):
        self._hue = hue
        self._sat = sat
        self.update()

    def set_value(self, v: float):
        self._value = max(0.0, min(1.0, v))
        self.update()

    def _x_to_value(self, x: int) -> float:
        return max(0.0, min(1.0, x / max(self.width() - 1, 1)))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._value = self._x_to_value(event.position().toPoint().x())
            self.update()
            self.value_changed.emit(self._value)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._value = self._x_to_value(event.position().toPoint().x())
            self.update()
            self.value_changed.emit(self._value)

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        full = QColor.fromHsvF(self._hue, self._sat, 1.0)
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor(0, 0, 0))
        grad.setColorAt(1.0, full)
        painter.fillRect(0, 0, w, h, grad)

        cx = int(self._value * (w - 1))
        pen = QPen(QColor(0, 0, 0))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(cx, 0, cx, h)
        pen.setColor(QColor(255, 255, 255))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(cx, 0, cx, h)


class ColorPicker(QWidget):
    """
    Roue teinte+saturation + slider luminosité.
    Émet color_changed(r, g, b) à chaque interaction.
    Appeler set_color() pour synchroniser depuis l'extérieur sans boucle de signal.
    """

    color_changed = Signal(int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hue = 0.0
        self._sat = 0.0
        self._val = 1.0

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self._wheel  = ColorWheel()
        self._slider = _ValueSlider()

        self._wheel.hs_changed.connect(self._on_hs)
        self._slider.value_changed.connect(self._on_value)

        lay.addWidget(self._wheel,  alignment=Qt.AlignHCenter)
        lay.addWidget(self._slider)

    def set_color(self, r: int, g: int, b: int):
        """Synchronise le picker sur une couleur RGB sans émettre color_changed."""
        h, s, v, _ = QColor(r, g, b).getHsvF()
        self._hue = max(0.0, h)   # h = -1 pour les couleurs achromatiques
        self._sat = s
        self._val = v
        self._wheel.set_hs(self._hue, self._sat)
        self._slider.set_color_params(self._hue, self._sat)
        self._slider.set_value(self._val)

    def _on_hs(self, h: float, s: float):
        self._hue = h
        self._sat = s
        self._slider.set_color_params(h, s)
        self._emit()

    def _on_value(self, v: float):
        self._val = v
        self._emit()

    def _emit(self):
        color = QColor.fromHsvF(self._hue, self._sat, self._val)
        self.color_changed.emit(color.red(), color.green(), color.blue())
