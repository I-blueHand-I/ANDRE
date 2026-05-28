from pathlib import Path

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame, QSizePolicy
from PySide6.QtCore import Qt, Signal, QThread, QEvent, QSize
from PySide6.QtGui import QPixmap

from ui.theme import ACCENT as _ACCENT
from ui.shared_widgets import frame_to_pixmap

_NAME_H = 16   # hauteur de l'overlay nom en bas de l'icône


class _AnimIcon(QWidget):
    """Icône carrée fluide : thumbnail cover + overlay nom."""

    hovered      = Signal(object)   # Animation | None
    load_clicked = Signal(object)   # Animation

    def __init__(self, animation, parent=None):
        super().__init__(parent)
        self._animation = animation
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self._thumb_lbl = QLabel(self)
        self._thumb_lbl.setAlignment(Qt.AlignCenter)
        self._thumb_lbl.setStyleSheet("background: #111111;")
        self._thumb_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._name_lbl = QLabel(animation.name, self)
        self._name_lbl.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self._name_lbl.setStyleSheet(
            "background: rgba(0,0,0,170); color: #cccccc; "
            "font-family: 'terminal grotesque'; font-size: 8px;"
        )
        self._name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._set_hover(False)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, w: int) -> int:
        return w

    def sizeHint(self) -> QSize:
        return QSize(80, 80)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        self._thumb_lbl.setGeometry(0, 0, w, h)
        self._name_lbl.setGeometry(0, h - _NAME_H, w, _NAME_H)
        if w > 0 and self._animation and self._animation.frame_count > 0:
            self._refresh_thumb(w, h)

    def _refresh_thumb(self, w: int, h: int):
        frame = self._animation.get_frame(0)
        px = frame_to_pixmap(frame).scaled(
            w, h, Qt.KeepAspectRatioByExpanding, Qt.FastTransformation
        )
        if px.width() > w or px.height() > h:
            x = (px.width()  - w) // 2
            y = (px.height() - h) // 2
            px = px.copy(x, y, w, h)
        self._thumb_lbl.setPixmap(px)

    def _set_hover(self, on: bool):
        self.setStyleSheet(
            f"border: 2px solid {_ACCENT};" if on else "border: 1px solid #2a2a2a;"
        )

    def event(self, e):
        if e.type() == QEvent.HoverEnter:
            self._set_hover(True)
            self.hovered.emit(self._animation)
        elif e.type() == QEvent.HoverLeave:
            self._set_hover(False)
            self.hovered.emit(None)
        return super().event(e)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.load_clicked.emit(self._animation)


class _ListRow(QWidget):
    """Ligne mode liste : nom + nb frames, hover → preview strip."""

    hovered      = Signal(object)
    load_clicked = Signal(object)

    def __init__(self, animation, parent=None):
        super().__init__(parent)
        self._animation = animation
        self.setFixedHeight(28)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setStyleSheet("background: transparent;")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 0, 8, 0)
        lay.setSpacing(8)

        name_lbl = QLabel(animation.name)
        name_lbl.setStyleSheet(
            "color: #cccccc; font-family: 'terminal grotesque'; font-size: 11px; background: transparent;"
        )
        name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(name_lbl, 1)

        count_lbl = QLabel(f"{animation.frame_count} fr")
        count_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        count_lbl.setStyleSheet(
            "color: #555555; font-family: 'terminal grotesque'; font-size: 9px; background: transparent;"
        )
        count_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(count_lbl)

        self._sep = QFrame(self)
        self._sep.setFrameShape(QFrame.HLine)
        self._sep.setStyleSheet("color: #2a2a2a;")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sep.setGeometry(0, self.height() - 1, self.width(), 1)

    def event(self, e):
        if e.type() == QEvent.HoverEnter:
            self.setStyleSheet("background: #2a2a2a;")
            self.hovered.emit(self._animation)
        elif e.type() == QEvent.HoverLeave:
            self.setStyleSheet("background: transparent;")
            self.hovered.emit(None)
        return super().event(e)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.load_clicked.emit(self._animation)


class _ScanWorker(QThread):
    """Charge animations ou vidéos depuis le disque dans un thread background."""
    scan_done = Signal(list)

    def __init__(self, folder_path: str, mode: str = "animation", parent=None):
        super().__init__(parent)
        self._folder_path = folder_path
        self._mode        = mode

    def run(self):
        folder = Path(self._folder_path)
        items  = []

        if self._mode == "animation":
            from engine.animation import Animation
            entries = sorted(
                [f for f in folder.iterdir() if Animation.is_animation_folder(f)],
                key=lambda f: f.name.lower()
            )
            for entry in entries:
                anim = Animation(entry)
                if anim.frame_count > 0:
                    items.append(anim)
        else:
            from engine.video import Video
            entries = sorted(
                [f for f in folder.iterdir() if Video.is_video_file(f)],
                key=lambda f: f.name.lower()
            )
            for entry in entries:
                vid = Video(entry)
                if vid.frame_count > 0:
                    items.append(vid)

        self.scan_done.emit(items)
