import json
from pathlib import Path

from utils import app_dir

DEFAULT_CONFIG = {
    "led_resolution": [21, 16],
    "udp_port": 37020,
    "udp_address": "255.255.255.255",
    "animations_folder": "",
    "mp4_folder": "",
    "midi_device": "",
    "midi_bindings": {},
    "key_bindings": {
        "PLAY_PAUSE": "Space",
        "PREV_FRAME": "Left",
        "NEXT_FRAME": "Right",
        "ADD_FRAME":  "+",
    },
    "palette": [
        "#FF0000", "#00FF00", "#0000FF", "#FFFF00",
        "#FF00FF", "#00FFFF", "#FF8800", "#8800FF",
        "#FFFFFF", "#888888"
    ]
}


class Config:
    def __init__(self):
        self._path = app_dir() / "config.json"
        self._data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data.update(saved)
                # Merge key_bindings: defaults apply unless user explicitly overrode them
                if "key_bindings" in saved:
                    self._data["key_bindings"] = {
                        **DEFAULT_CONFIG["key_bindings"],
                        **saved["key_bindings"],
                    }
            except Exception as e:
                print(f"Config load error: {e}")

    def save(self):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            print(f"Config save error: {e}")

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self.save()

