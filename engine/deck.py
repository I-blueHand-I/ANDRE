import time
import numpy as np

from engine.constants import ENGINE_FPS as _ENGINE_FPS


class Deck:
    """Plays an Animation or Video at a configurable FPS using a time accumulator."""

    def __init__(self):
        self._animation = None
        self._fps: float = 15.0
        self._frame_dur: float = 1.0 / 15.0
        self._frame_index: int = 0
        self._accumulator: float = 0.0
        self._last_tick: float = time.perf_counter()
        self._paused: bool = True
        self._last_frame = None
        self._cueing: bool = False
        self._has_fps_native: bool = False

    def load(self, animation) -> None:
        # Null out animation first so tick() returns None during the swap (#28)
        self._animation = None
        # Compute potentially-slow first frame before modifying shared state
        first_frame = animation.get_frame(0) if animation.frame_count > 0 else None
        self._frame_index = 0
        self._accumulator = 0.0
        self._last_tick = time.perf_counter()
        self._cueing = False
        self._has_fps_native = hasattr(animation, 'fps_native')
        self._last_frame = first_frame
        self._animation = animation  # install last — tick() sees complete state

    def unload(self) -> None:
        self._animation = None
        self._last_frame = None   # prevent stale preview after unload (#33)

    def set_fps(self, fps: int) -> None:
        self._fps = max(1, int(fps))
        self._frame_dur = 1.0 / self._fps

    def set_paused(self, paused: bool) -> None:
        self._paused = paused

    def cue_start(self) -> None:
        self._cueing = True
        self._frame_index = 0
        self._accumulator = 0.0
        self._last_tick = time.perf_counter()

    def cue_end(self) -> None:
        self._cueing = False
        if self._paused:
            self._frame_index = 0
            self._accumulator = 0.0
            self._last_tick = time.perf_counter()

    def tick(self, now: float) -> "np.ndarray | None":
        anim = self._animation  # snapshot — atomic under GIL
        if anim is None or anim.frame_count == 0:
            self._last_tick = now
            return None

        # Snapshot both flags together to reduce the inter-read race window (#29)
        paused = self._paused
        cueing = self._cueing
        if paused and not cueing:
            self._last_tick = now
            return None

        dt = now - self._last_tick
        self._last_tick = now

        frame_dur = self._frame_dur
        if self._has_fps_native:
            capped_fps = min(max(self._fps, anim.fps_native), _ENGINE_FPS)
            frame_dur = 1.0 / capped_fps

        self._accumulator += dt
        while self._accumulator >= frame_dur:
            self._frame_index = (self._frame_index + 1) % anim.frame_count
            self._accumulator -= frame_dur

        self._last_frame = anim.get_frame(self._frame_index)
        return self._last_frame

    @property
    def last_frame(self):
        return self._last_frame

    @property
    def has_animation(self) -> bool:
        return self._animation is not None
