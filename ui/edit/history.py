from collections import deque
import numpy as np


class History:
    """
    Pile undo/redo par snapshots complets (frames + index courant).
    Chaque snapshot est une copie indépendante — pas de référence partagée.
    """

    def __init__(self, max_levels: int = 20):
        self._undo: deque = deque(maxlen=max_levels)
        self._redo: deque = deque()

    def push(self, frames: list[np.ndarray], current: int):
        self._undo.append(([f.copy() for f in frames], current))
        self._redo.clear()

    def undo(self, frames: list[np.ndarray], current: int) -> tuple | None:
        if not self._undo:
            return None
        self._redo.append(([f.copy() for f in frames], current))
        return self._undo.pop()

    def redo(self, frames: list[np.ndarray], current: int) -> tuple | None:
        if not self._redo:
            return None
        self._undo.append(([f.copy() for f in frames], current))
        return self._redo.pop()

