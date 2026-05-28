import threading
from pathlib import Path
import numpy as np

_VIDEO_EXTENSIONS   = {'.mp4', '.mov'}
_PREVIEW_W          = 128
_PREVIEW_H          = 72
_PREVIEW_MAX_FRAMES = 60
_MAX_SEQ_ADVANCE    = 6   # sauts ≤ N frames → lecture séquentielle (pas de seek)

try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False


class Video:
    """
    Vidéo MP4/MOV en streaming séquentiel via cv2.
    get_frame() lit séquentiellement — seek uniquement au bouclage ou accès non-séquentiel.
    Thread-safe via un lock interne.
    _preview_frames : petits tableaux numpy (128×72) chargés une fois à l'init,
    utilisés par le hover-preview sans jamais toucher au VideoCapture principal.
    """

    def __init__(self, path: Path):
        self.path    = Path(path)
        self.name    = self.path.stem
        self._cap    = None
        self._frame_count  = 0
        self._fps_native   = 30.0
        self._current_idx  = -1
        self._current_frame: np.ndarray | None = None
        self._lock   = threading.Lock()
        self._preview_frames: list[np.ndarray] = []
        self._load()

    def _load(self):
        if not _HAS_CV2:
            print("OpenCV non installé — impossible de charger les vidéos")
            return
        cap = cv2.VideoCapture(str(self.path))
        if not cap.isOpened():
            print(f"Video: impossible d'ouvrir {self.path.name}")
            return
        self._cap         = cap
        self._frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._fps_native  = cap.get(cv2.CAP_PROP_FPS) or 30.0
        self._seek(0)
        self._preload_preview()

    def _preload_preview(self):
        if not _HAS_CV2 or self._frame_count == 0:
            return
        cap = cv2.VideoCapture(str(self.path))
        if not cap.isOpened():
            return
        count = min(_PREVIEW_MAX_FRAMES, self._frame_count)
        for _ in range(count):
            ret, frame = cap.read()
            if not ret:
                break
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            small = cv2.resize(rgb, (_PREVIEW_W, _PREVIEW_H), interpolation=cv2.INTER_AREA)
            self._preview_frames.append(small)
        cap.release()

    # ── Lecture ───────────────────────────────────────────────────────────────

    def get_frame(self, index: int) -> np.ndarray:
        with self._lock:
            if self._cap is None or self._frame_count == 0:
                return np.zeros((16, 21, 3), dtype=np.uint8)

            target = index % self._frame_count

            if target == self._current_idx:
                pass
            elif self._current_idx < target <= self._current_idx + _MAX_SEQ_ADVANCE:
                while self._current_idx < target:
                    self._read_next()
            else:
                self._seek(target)

            return (
                self._current_frame
                if self._current_frame is not None
                else np.zeros((16, 21, 3), dtype=np.uint8)
            )

    def _read_next(self):
        ret, frame = self._cap.read()
        if ret:
            self._current_idx  += 1
            self._current_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            self._seek(0)

    def _seek(self, index: int):
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ret, frame = self._cap.read()
        if ret:
            self._current_idx   = index
            self._current_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def get_preview_frame(self, index: int) -> np.ndarray:
        """Returns a preloaded small frame (128×72) — no lock, zero contention."""
        if not self._preview_frames:
            return self.get_frame(index)
        return self._preview_frames[index % len(self._preview_frames)]

    # ── Propriétés ────────────────────────────────────────────────────────────

    @property
    def frame_count(self) -> int:
        return max(0, self._frame_count)

    @property
    def fps_native(self) -> float:
        return self._fps_native

    # ── Cycle de vie ──────────────────────────────────────────────────────────

    def release(self):
        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None

    def __del__(self):
        self.release()

    # ── Utilitaire ────────────────────────────────────────────────────────────

    @staticmethod
    def is_video_file(path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in _VIDEO_EXTENSIONS
