from collections import deque
import numpy as np


class ToolResult:
    __slots__ = ("modified", "picked_color")

    def __init__(self, modified: bool = False, picked_color: tuple | None = None):
        self.modified     = modified
        self.picked_color = picked_color   # (r, g, b) ou None


# ── Brush ─────────────────────────────────────────────────────────────────────

class BrushTool:
    def press(self, pixels: np.ndarray, col: int, row: int, color: tuple, thickness: int = 1) -> ToolResult:
        return self._paint(pixels, col, row, color, thickness)

    def drag(self, pixels: np.ndarray, col: int, row: int, color: tuple, thickness: int = 1) -> ToolResult:
        return self._paint(pixels, col, row, color, thickness)

    def _paint(self, pixels: np.ndarray, col: int, row: int, color: tuple, thickness: int) -> ToolResult:
        H, W  = pixels.shape[:2]
        half  = thickness // 2
        r0    = max(0, row - half)
        r1    = min(H, row - half + thickness)
        c0    = max(0, col - half)
        c1    = min(W, col - half + thickness)
        sub   = pixels[r0:r1, c0:c1]
        c_arr = np.array(color, dtype=np.uint8)
        mask  = np.any(sub != c_arr, axis=2)
        if mask.any():
            sub[mask] = c_arr
            return ToolResult(modified=True)
        return ToolResult()


# ── Eraser ────────────────────────────────────────────────────────────────────

class EraseTool:
    def press(self, pixels: np.ndarray, col: int, row: int, color: tuple, thickness: int = 1) -> ToolResult:
        return self._erase(pixels, col, row, thickness)

    def drag(self, pixels: np.ndarray, col: int, row: int, color: tuple, thickness: int = 1) -> ToolResult:
        return self._erase(pixels, col, row, thickness)

    def _erase(self, pixels: np.ndarray, col: int, row: int, thickness: int) -> ToolResult:
        H, W = pixels.shape[:2]
        half = thickness // 2
        r0   = max(0, row - half)
        r1   = min(H, row - half + thickness)
        c0   = max(0, col - half)
        c1   = min(W, col - half + thickness)
        sub  = pixels[r0:r1, c0:c1]
        if sub.any():
            sub[:] = 0
            return ToolResult(modified=True)
        return ToolResult()


# ── Fill ──────────────────────────────────────────────────────────────────────

class FillTool:
    def press(self, pixels: np.ndarray, col: int, row: int, color: tuple, thickness: int = 1) -> ToolResult:
        H, W = pixels.shape[:2]
        target = tuple(pixels[row, col])
        if target == color:
            return ToolResult()

        queue   = deque([(col, row)])
        visited = set()
        while queue:
            c, r = queue.popleft()
            if (c, r) in visited or not (0 <= c < W and 0 <= r < H):
                continue
            if tuple(pixels[r, c]) != target:
                continue
            visited.add((c, r))
            pixels[r, c] = color
            queue.extend([(c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)])

        return ToolResult(modified=bool(visited))

    def drag(self, pixels: np.ndarray, col: int, row: int, color: tuple, thickness: int = 1) -> ToolResult:
        return ToolResult()


# ── Eyedropper ────────────────────────────────────────────────────────────────

class EyedropperTool:
    def press(self, pixels: np.ndarray, col: int, row: int, color: tuple, thickness: int = 1) -> ToolResult:
        r, g, b = int(pixels[row, col, 0]), int(pixels[row, col, 1]), int(pixels[row, col, 2])
        return ToolResult(picked_color=(r, g, b))

    def drag(self, pixels: np.ndarray, col: int, row: int, color: tuple, thickness: int = 1) -> ToolResult:
        return ToolResult()


# ── Registre ──────────────────────────────────────────────────────────────────

TOOLS: dict = {
    "brush":      BrushTool(),
    "fill":       FillTool(),
    "eyedropper": EyedropperTool(),
}

_ERASE_TOOL = EraseTool()
