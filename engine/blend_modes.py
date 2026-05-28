import numpy as np


def _blend_normal(fa: np.ndarray, fb: np.ndarray) -> np.ndarray:
    return fa

def _blend_screen(fa: np.ndarray, fb: np.ndarray) -> np.ndarray:
    fa_f = fa.astype(np.float32)
    fb_f = fb.astype(np.float32)
    return np.clip(fa_f + fb_f - fa_f * fb_f / 255.0, 0, 255).astype(np.uint8)

def _blend_overlay(fa: np.ndarray, fb: np.ndarray) -> np.ndarray:
    fa_f = fa.astype(np.float32)
    fb_f = fb.astype(np.float32)
    dark  = 2.0 * fa_f * fb_f / 255.0
    light = 255.0 - 2.0 * (255.0 - fa_f) * (255.0 - fb_f) / 255.0
    return np.where(fa_f < 128.0, dark, light).clip(0, 255).astype(np.uint8)

def _blend_multiply(fa: np.ndarray, fb: np.ndarray) -> np.ndarray:
    return np.clip(fa.astype(np.float32) * fb.astype(np.float32) / 255.0, 0, 255).astype(np.uint8)

def _blend_addition(fa: np.ndarray, fb: np.ndarray) -> np.ndarray:
    return np.clip(fa.astype(np.float32) + fb.astype(np.float32), 0, 255).astype(np.uint8)

def _blend_subtract(fa: np.ndarray, fb: np.ndarray) -> np.ndarray:
    return np.clip(fa.astype(np.float32) - fb.astype(np.float32), 0, 255).astype(np.uint8)

def _blend_difference(fa: np.ndarray, fb: np.ndarray) -> np.ndarray:
    return np.abs(fa.astype(np.int16) - fb.astype(np.int16)).clip(0, 255).astype(np.uint8)

def _blend_lighten(fa: np.ndarray, fb: np.ndarray) -> np.ndarray:
    return np.maximum(fa, fb)

def _blend_darken(fa: np.ndarray, fb: np.ndarray) -> np.ndarray:
    return np.minimum(fa, fb)


BLEND_MODES: dict = {
    "NORMAL":     _blend_normal,
    "SCREEN":     _blend_screen,
    "OVERLAY":    _blend_overlay,
    "MULTIPLY":   _blend_multiply,
    "ADDITION":   _blend_addition,
    "SUBTRACT":   _blend_subtract,
    "DIFFERENCE": _blend_difference,
    "LIGHTEN":    _blend_lighten,
    "DARKEN":     _blend_darken,
}
