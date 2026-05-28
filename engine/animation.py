from pathlib import Path
import numpy as np

try:
    from PIL import Image as PilImage
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


def _frame_sort_key(path: Path):
    """Trie numériquement si le stem est un entier, sinon alphabétiquement."""
    try:
        return (0, int(path.stem))
    except ValueError:
        return (1, path.stem)


class Animation:
    """
    Animation pixel art : un dossier contenant des PNG numérotés.
    Frames stockées en RGB numpy à la résolution native.
    """

    def __init__(self, folder: Path):
        self.path = Path(folder)
        self.name = self.path.name
        self.frames: list[np.ndarray] = []
        self._load()

    def _load(self):
        if not _HAS_PIL:
            print("Pillow non installé — impossible de charger les animations")
            return
        if not self.path.is_dir():
            print(f"Animation: {self.path} n'est pas un dossier")
            return

        pngs = sorted(self.path.glob("*.png"), key=_frame_sort_key)
        if not pngs:
            print(f"Animation: aucun PNG dans {self.path.name}")
            return

        for png in pngs:
            try:
                img = PilImage.open(png)
                self.frames.append(np.array(img.convert("RGB"), dtype=np.uint8))
            except Exception as e:
                print(f"Frame load error {png.name}: {e}")

    def get_frame(self, index: int) -> np.ndarray:
        if not self.frames:
            return np.zeros((16, 21, 3), dtype=np.uint8)
        return self.frames[index % len(self.frames)]

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @staticmethod
    def is_animation_folder(path: Path) -> bool:
        """Vérifie si un dossier contient au moins un PNG."""
        return path.is_dir() and any(path.glob("*.png"))
