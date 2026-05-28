import numpy as np

try:
    import cv2
    _HAS_CV2 = True
    _CV2_INTERP = {
        "NEAREST": cv2.INTER_NEAREST,
        "BICUBIC": cv2.INTER_CUBIC,
        "AREA":    cv2.INTER_AREA,
        "LINEAR":  cv2.INTER_LINEAR,
    }
except ImportError:
    _HAS_CV2 = False
    _CV2_INTERP = {}

try:
    from PIL import Image as PilImage
    _HAS_PIL = True
    _PIL_INTERP = {
        "NEAREST": PilImage.NEAREST,
        "BICUBIC": PilImage.BICUBIC,
        "AREA":    PilImage.LANCZOS,
        "LINEAR":  PilImage.BILINEAR,
    }
except ImportError:
    _HAS_PIL = False
    _PIL_INTERP = {}


def resize_frame(frame: np.ndarray, w: int, h: int, mode: str = "NEAREST") -> np.ndarray:
    """Resize a (H, W, 3) uint8 frame to (h, w, 3). No-op if already the right size."""
    if frame.shape[1] == w and frame.shape[0] == h:
        return frame

    mode = mode.upper()

    if _HAS_CV2:
        interp = _CV2_INTERP.get(mode, cv2.INTER_NEAREST)
        return cv2.resize(frame, (w, h), interpolation=interp)

    if _HAS_PIL:
        resample = _PIL_INTERP.get(mode, PilImage.NEAREST)
        return np.array(PilImage.fromarray(frame, "RGB").resize((w, h), resample))

    # Fallback numpy nearest-neighbor
    fh, fw = frame.shape[:2]
    ri = (np.arange(h) * fh // h).astype(int)
    ci = (np.arange(w) * fw // w).astype(int)
    return frame[np.ix_(ri, ci)]
