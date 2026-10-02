from pathlib import Path
import numpy as np

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame, QSizePolicy
from PySide6.QtCore import Qt, Signal, QThread, QEvent, QSize
from PySide6.QtGui import QPixmap

from ui.theme import ACCENT as _ACCENT
from ui.shared_widgets import frame_to_pixmap

_NAME_H = 16   # hauteur de l'overlay nom en bas de l'icône


class _FolderEntry:
    """Lightweight representation of an organizational subfolder in the bank."""

    def __init__(self, path: Path, preview_source=None,
                 item_count: int = 0):
        self.path = path
        self.name = path.name
        self._preview_source = preview_source
        self.item_count = item_count
        if preview_source is not None and preview_source.frame_count > 0:
            self._preview_frame = preview_source.get_frame(0)
            self.frame_count = preview_source.frame_count
        else:
            self._preview_frame = None
            self.frame_count = 0

    def get_frame(self, idx: int = 0) -> np.ndarray | None:
        if self._preview_source is not None:
            return self._preview_source.get_frame(idx)
        return self._preview_frame

    def get_preview_frame(self, idx: int = 0) -> np.ndarray | None:
        if self._preview_source is not None and hasattr(self._preview_source, 'get_preview_frame'):
            return self._preview_source.get_preview_frame(idx)
        return self.get_frame(idx)


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


class _FolderIcon(QWidget):
    """Icone carrée pour un dossier organisationnel."""

    hovered        = Signal(object)
    folder_clicked = Signal(object)   # _FolderEntry

    def __init__(self, folder_entry: _FolderEntry, parent=None):
        super().__init__(parent)
        self._folder = folder_entry
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self._thumb_lbl = QLabel(self)
        self._thumb_lbl.setAlignment(Qt.AlignCenter)
        self._thumb_lbl.setStyleSheet("background: #111111;")
        self._thumb_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._name_lbl = QLabel(f"\U0001F4C1 {folder_entry.name}", self)
        self._name_lbl.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self._name_lbl.setStyleSheet(
            "background: rgba(0,0,0,200); color: #e0e0e0; "
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
        if w > 0 and self._folder._preview_frame is not None:
            self._refresh_thumb(w, h)

    def _refresh_thumb(self, w: int, h: int):
        frame = self._folder._preview_frame
        if frame is None:
            return
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
            f"border: 2px solid {_ACCENT};" if on else "border: 1px solid #444444;"
        )

    def event(self, e):
        if e.type() == QEvent.HoverEnter:
            self._set_hover(True)
            self.hovered.emit(self._folder)
        elif e.type() == QEvent.HoverLeave:
            self._set_hover(False)
            self.hovered.emit(None)
        return super().event(e)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.folder_clicked.emit(self._folder)


class _FolderRow(QWidget):
    """Ligne mode liste pour un dossier organisationnel."""

    hovered        = Signal(object)
    folder_clicked = Signal(object)

    def __init__(self, folder_entry: _FolderEntry, parent=None):
        super().__init__(parent)
        self._folder = folder_entry
        self.setFixedHeight(28)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setStyleSheet("background: transparent;")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 0, 8, 0)
        lay.setSpacing(8)

        name_lbl = QLabel(f"\U0001F4C1 {folder_entry.name}")
        name_lbl.setStyleSheet(
            "color: #e0e0e0; font-family: 'terminal grotesque'; font-size: 11px; background: transparent;"
        )
        name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(name_lbl, 1)

        count_lbl = QLabel(f"{folder_entry.item_count} items")
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
            self.hovered.emit(self._folder)
        elif e.type() == QEvent.HoverLeave:
            self.setStyleSheet("background: transparent;")
            self.hovered.emit(None)
        return super().event(e)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.folder_clicked.emit(self._folder)


class _ScanWorker(QThread):
    """Charge animations ou vidéos depuis le disque dans un thread background."""
    scan_done = Signal(list, list)   # (folders, items)

    def __init__(self, folder_path: str, mode: str = "animation",
                 detect_folders: bool = False, parent=None):
        super().__init__(parent)
        self._folder_path    = folder_path
        self._mode           = mode
        self._detect_folders = detect_folders

    def run(self):
        folder  = Path(self._folder_path)
        folders: list[_FolderEntry] = []
        items:   list = []

        if self._mode == "animation":
            self._scan_animations(folder, folders, items)
        else:
            self._scan_videos(folder, folders, items)

        self.scan_done.emit(folders, items)

    def _scan_animations(self, folder: Path, folders: list, items: list):
        from engine.animation import Animation

        all_entries = sorted(
            [f for f in folder.iterdir() if f.is_dir() and not f.name.startswith(".")],
            key=lambda f: f.name.lower()
        )
        for entry in all_entries:
            if Animation.is_animation_folder(entry):
                anim = Animation(entry)
                if anim.frame_count > 0:
                    items.append(anim)
            elif self._detect_folders:
                children = sorted(
                    [c for c in entry.iterdir() if Animation.is_animation_folder(c)],
                    key=lambda c: c.name.lower()
                )
                if not children:
                    continue
                first = Animation(children[0])
                source = first if first.frame_count > 0 else None
                folders.append(_FolderEntry(entry, source, len(children)))

    def _scan_videos(self, folder: Path, folders: list, items: list):
        from engine.video import Video

        all_entries = sorted(
            [f for f in folder.iterdir() if not f.name.startswith(".")],
            key=lambda f: f.name.lower()
        )
        for entry in all_entries:
            if Video.is_video_file(entry):
                vid = Video(entry)
                if vid.frame_count > 0:
                    items.append(vid)
            elif entry.is_dir() and self._detect_folders:
                children = sorted(
                    [c for c in entry.iterdir() if Video.is_video_file(c)],
                    key=lambda c: c.name.lower()
                )
                if not children:
                    continue
                first = Video(children[0])
                source = first if first.frame_count > 0 else None
                folders.append(_FolderEntry(entry, source, len(children)))
