import numpy as np


class EditAnimation:
    """
    Duck-typed animation wrapper autour de la liste de frames de la timeline edit.
    Compatible avec Deck.load() — expose frame_count et get_frame(i).
    Lit la liste live à chaque accès pour refléter les modifications en cours.
    """

    def __init__(self, get_frames):
        self._get_frames = get_frames   # callable: () -> list[np.ndarray]

    @property
    def frame_count(self) -> int:
        return len(self._get_frames())

    def get_frame(self, i: int) -> np.ndarray:
        frames = self._get_frames()
        if not frames:
            return np.zeros((16, 21, 3), dtype=np.uint8)
        return frames[i % len(frames)]
