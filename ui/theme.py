import json
from pathlib import Path

from utils import app_dir

_path = app_dir() / "themes" / "default.json"


def _load() -> dict:
    try:
        with open(_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _c(d: dict, key: str, fallback: str) -> str:
    return d.get(key, fallback)


_t = _load()

ACCENT            = _c(_t, "accent",           "#e0156b")

BG_DARKEST        = _c(_t, "bg_darkest",       "#111111")
BG_DARK           = _c(_t, "bg_dark",          "#1a1a1a")
BG_MAIN           = _c(_t, "bg_main",          "#1e1e1e")
BG_PANEL          = _c(_t, "bg_panel",         "#252525")
BG_BUTTON         = _c(_t, "bg_button",        "#333333")
BG_BUTTON_HOVER   = _c(_t, "bg_button_hover",  "#444444")
BG_BUTTON_ACTIVE  = _c(_t, "bg_button_active", "#555555")

BORDER            = _c(_t, "border",           "#666666")

TEXT              = _c(_t, "text",             "#ffffff")
TEXT_MUTED        = _c(_t, "text_muted",       "#aaaaaa")
TEXT_DIM          = _c(_t, "text_dim",         "#888888")
TEXT_FPS          = _c(_t, "text_fps",         "#cc2222")

DECK_A            = _c(_t, "deck_a",           "#881111")
DECK_A_HOVER      = _c(_t, "deck_a_hover",     "#aa2222")
DECK_A_BRIGHT     = _c(_t, "deck_a_bright",    "#cc2222")
DECK_B            = _c(_t, "deck_b",           "#116611")
DECK_B_HOVER      = _c(_t, "deck_b_hover",     "#228822")
DECK_B_BRIGHT     = _c(_t, "deck_b_bright",    "#22aa22")

TAB_ACTIVE        = _c(_t, "tab_active",       "#2d7a4f")
TAB_INACTIVE      = _c(_t, "tab_inactive",     "#1a4d32")
TAB_HOVER         = _c(_t, "tab_hover",        "#3d9966")
TAB_BORDER        = _c(_t, "tab_border",       "#4dcc88")

FONT_UI           = "terminal grotesque"   # loaded from project/fonts/terminal-grotesque.ttf
