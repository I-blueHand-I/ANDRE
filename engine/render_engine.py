import time
import numpy as np
import cv2 as _cv2
from PySide6.QtCore import QThread, Signal

from engine.constants import ENGINE_FPS, SIDE_A
from engine.deck import Deck
from engine.blend_modes import BLEND_MODES
from engine.resize import resize_frame

_NORMAL_BLEND = BLEND_MODES["NORMAL"]


def _apply_hsv(frame: np.ndarray, hue_shift: float,
               sat_mult: float, val_mult: float) -> np.ndarray:
    hsv = _cv2.cvtColor(frame, _cv2.COLOR_RGB2HSV).astype(np.float32)
    if hue_shift != 0.0:
        hsv[:, :, 0] = (hsv[:, :, 0] + hue_shift / 2.0) % 180.0
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * sat_mult, 0, 255)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * val_mult, 0, 255)
    return _cv2.cvtColor(hsv.astype(np.uint8), _cv2.COLOR_HSV2RGB)


class RenderEngine(QThread):
    frame_ready  = Signal(object)   # mixed frame (H, W, 3) uint8
    deck_a_ready = Signal(object)   # frame deck A pour preview UI
    deck_b_ready = Signal(object)   # frame deck B pour preview UI

    def __init__(self, config):
        super().__init__()
        self.config  = config
        self.deck_a  = Deck()
        self.deck_b  = Deck()
        self._running = False

        self._crossfader: float = 0.5
        self._interp_mode: str  = "AREA"

        self._blend_mode_a: str = "NORMAL"
        self._blend_mode_b: str = "NORMAL"

        self._rgb: tuple[float, float, float]       = (1.0, 1.0, 1.0)
        self._hsv: tuple[bool, float, float, float] = (False, 0.0, 1.0, 1.0)

        self._strobe_active:      bool               = False
        self._strobe_freq:        int                = 5
        self._strobe_color:       tuple[int,int,int]  = (0, 0, 0)
        self._strobe_phase:       float              = 0.0
        self._strobe_vis:         bool               = True
        self._strobe_blend_mode:  str                = "NORMAL"

        res = config.get("led_resolution", [21, 16])
        self._resolution: tuple[int, int] = (int(res[0]), int(res[1]))

        self._black:         np.ndarray | None = None
        self._strobe_buf:    np.ndarray | None = None
        self._frozen_prev_a: tuple | None = None  # (raw_id, resized)
        self._frozen_prev_b: tuple | None = None

        self._tick: int = 0

    def refresh_resolution(self) -> None:
        res = self.config.get("led_resolution", [21, 16])
        self._resolution = (int(res[0]), int(res[1]))
        self._black = None
        self._strobe_buf = None
        self._frozen_prev_a = None
        self._frozen_prev_b = None

    # ── Setters thread-safe ───────────────────────────────────────────────────

    def set_crossfader(self, value: float) -> None:
        self._crossfader = max(0.0, min(1.0, value))

    def set_interpolation(self, mode: str) -> None:
        self._interp_mode = mode.upper()
        self._frozen_prev_a = None
        self._frozen_prev_b = None

    def set_rgb(self, r: float, g: float, b: float) -> None:
        self._rgb = (r, g, b)

    def set_hsv(self, hue_on: bool, hue_deg: float,
                sat_mult: float, val_mult: float) -> None:
        self._hsv = (hue_on, hue_deg, sat_mult, val_mult)

    def set_blend_mode(self, deck: str, mode: str) -> None:
        if deck == SIDE_A:
            self._blend_mode_a = mode if mode in BLEND_MODES else "NORMAL"
        else:
            self._blend_mode_b = mode if mode in BLEND_MODES else "NORMAL"

    def set_strobe_active(self, active: bool) -> None:
        self._strobe_active = active
        if active:
            self._strobe_phase = time.perf_counter()
            self._strobe_vis   = True
        else:
            self._strobe_vis = True

    def set_strobe_freq(self, freq: int) -> None:
        self._strobe_freq = max(1, int(freq))

    def set_strobe_color(self, r: int, g: int, b: int) -> None:
        self._strobe_color = (int(r), int(g), int(b))
        self._strobe_buf = None

    def set_strobe_blend_mode(self, mode: str) -> None:
        self._strobe_blend_mode = mode if mode in BLEND_MODES else "NORMAL"

    # ── Boucle de rendu ───────────────────────────────────────────────────────

    def run(self):
        self._running = True
        while self._running:
            t0 = time.perf_counter()
            self._tick += 1

            w, h = self._resolution

            if self._black is None or self._black.shape != (h, w, 3):
                self._black = np.zeros((h, w, 3), dtype=np.uint8)
            black = self._black

            raw_a = self.deck_a.tick(t0)
            raw_b = self.deck_b.tick(t0)

            if raw_a is not None:
                fa = resize_frame(raw_a, w, h, self._interp_mode)
                self._frozen_prev_a = None
                self.deck_a_ready.emit(fa)
            else:
                fa = black
                last = self.deck_a.last_frame
                if last is not None:
                    cached = self._frozen_prev_a
                    if cached is None or cached[0] is not last:
                        resized = resize_frame(last, w, h, self._interp_mode)
                        self._frozen_prev_a = (last, resized)
                    self.deck_a_ready.emit(self._frozen_prev_a[1])

            if raw_b is not None:
                fb = resize_frame(raw_b, w, h, self._interp_mode)
                self._frozen_prev_b = None
                self.deck_b_ready.emit(fb)
            else:
                fb = black
                last = self.deck_b.last_frame
                if last is not None:
                    cached = self._frozen_prev_b
                    if cached is None or cached[0] is not last:
                        resized = resize_frame(last, w, h, self._interp_mode)
                        self._frozen_prev_b = (last, resized)
                    self.deck_b_ready.emit(self._frozen_prev_b[1])

            blend_a = BLEND_MODES.get(self._blend_mode_a, _NORMAL_BLEND)
            blend_b = BLEND_MODES.get(self._blend_mode_b, _NORMAL_BLEND)
            if blend_a is not _NORMAL_BLEND:
                fa = blend_a(fa, fb)
            if blend_b is not _NORMAL_BLEND:
                fb = blend_b(fb, fa)

            cf = self._crossfader
            if cf <= 0.0:
                mixed = fa
            elif cf >= 1.0:
                mixed = fb
            else:
                mixed = (
                    (1.0 - cf) * fa.astype(np.float32)
                    + cf * fb.astype(np.float32)
                ).astype(np.uint8)

            hue_on, hue_deg, sat_m, val_m = self._hsv
            if hue_on or sat_m != 1.0 or val_m != 1.0:
                mixed = _apply_hsv(mixed, hue_deg if hue_on else 0.0, sat_m, val_m)

            r, g, b = self._rgb
            if r != 1.0 or g != 1.0 or b != 1.0:
                f = mixed.astype(np.float32)
                f[:, :, 0] *= r
                f[:, :, 1] *= g
                f[:, :, 2] *= b
                mixed = np.clip(f, 0, 255).astype(np.uint8)

            if self._strobe_active:
                half = 0.5 / self._strobe_freq
                if t0 - self._strobe_phase >= half:
                    self._strobe_vis = not self._strobe_vis
                    self._strobe_phase = t0
                if not self._strobe_vis:
                    if self._strobe_buf is None or self._strobe_buf.shape != (h, w, 3):
                        self._strobe_buf = np.empty((h, w, 3), dtype=np.uint8)
                    buf = self._strobe_buf   # local snapshot before main-thread can null it
                    buf[:] = self._strobe_color
                    strobe_blend = BLEND_MODES.get(self._strobe_blend_mode, _NORMAL_BLEND)
                    mixed = strobe_blend(buf, mixed)

            self.frame_ready.emit(mixed)

            elapsed = time.perf_counter() - t0
            sleep = max(0.0, (1.0 / ENGINE_FPS) - elapsed)
            if sleep > 0:
                time.sleep(sleep)

    def stop(self):
        self._running = False
