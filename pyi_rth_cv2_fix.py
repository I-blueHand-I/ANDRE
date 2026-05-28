import importlib
import importlib.util
import os
import sys

_original_import_module = importlib.import_module


def _patched_import_module(name, package=None):
    if name == "cv2" and hasattr(sys, "OpenCV_LOADER"):
        for p in sys.path:
            for candidate in [
                os.path.join(p, "cv2.abi3.so"),
                os.path.join(p, "cv2", "cv2.abi3.so"),
            ]:
                if os.path.exists(candidate):
                    spec = importlib.util.spec_from_file_location("cv2", candidate)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    return mod
    return _original_import_module(name, package)


importlib.import_module = _patched_import_module
