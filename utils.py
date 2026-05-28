import sys
from pathlib import Path


def app_dir() -> Path:
    """Return the application root directory.

    When running as a compiled exe (PyInstaller / Nuitka), __file__ is
    unreliable; sys.executable always points to the .exe itself, so its
    parent is the folder where the exe lives — which is where data files
    (config.json, themes/, fonts/) are expected to be.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent
