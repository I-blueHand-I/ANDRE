from PySide6.QtWidgets import QLabel
from ui.theme import ACCENT as _ACCENT

_MIDI_BTN = """
QPushButton {
    background-color: #2e2e2e;
    color: #888888;
    border: 1px solid #444444;
    padding: 2px 8px;
    font-family: 'terminal grotesque', monospace;
    font-size: 10px;
    border-radius: 2px;
}
QPushButton:hover { background-color: #3a3a3a; color: #aaaaaa; }
QPushButton:checked {
    background-color: #663300;
    color: #ff8833;
    border: 1px solid #ff6600;
}
"""

_STROBE_BTN = f"""
QPushButton {{
    background-color: #2e2e2e;
    border: 2px solid #666666;
    border-radius: 10px;
}}
QPushButton:hover {{
    background-color: #3a3a3a;
    border: 2px solid #999999;
}}
QPushButton:pressed {{
    background-color: {_ACCENT};
    border: 2px solid #ff4499;
}}
"""

_HUE_TOGGLE = f"""
QPushButton {{
    background-color: #2e2e2e;
    color: #555555;
    border: 1px solid #444444;
    padding: 2px 6px;
    font-family: 'terminal grotesque', monospace;
    font-size: 9px;
    font-weight: bold;
}}
QPushButton:checked {{
    background-color: #1a1a1a;
    color: {_ACCENT};
    border: 1px solid {_ACCENT};
}}
QPushButton:hover:!checked {{ background-color: #3a3a3a; }}
"""


def _label(text: str, color: str = "white", size: int = 16) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {color}; font-family: 'terminal grotesque', monospace; "
        f"font-size: {size}px; font-weight: bold;"
    )
    return lbl


def _slider_style(track: str, fill: str) -> str:
    return f"""
    QSlider::groove:horizontal {{
        background: {track};
        height: 6px;
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: #cccccc;
        width: 6px; height: 22px;
        margin: -8px 0;
        border-radius: 0;
    }}
    QSlider::sub-page:horizontal {{
        background: {fill};
        border-radius: 3px;
    }}
    """
