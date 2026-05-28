from ui.theme import ACCENT as _ACCENT

_VSLIDER = f"""
QSlider::groove:vertical {{
    background: #3a3a3a;
    width: 4px;
    border-radius: 2px;
}}
QSlider::handle:vertical {{
    background: {_ACCENT};
    height: 12px; width: 22px;
    margin: 0 -9px;
    border-radius: 0px;
}}
QSlider::add-page:vertical {{
    background: {_ACCENT};
    border-radius: 2px;
}}
QSlider::sub-page:vertical {{
    background: #3a3a3a;
    border-radius: 2px;
}}
"""

_COMBO = """
QComboBox {
    background-color: #1a1a1a;
    color: #dd2222;
    border: 1px solid #555555;
    padding: 4px 10px;
    font-family: 'terminal grotesque', monospace;
    font-weight: bold;
    font-size: 12px;
    min-width: 120px;
}
QComboBox::drop-down { border: none; width: 22px; }
QComboBox::down-arrow { width: 10px; height: 10px; }
QComboBox QAbstractItemView {
    background-color: #2a2a2a;
    color: white;
    selection-background-color: #444444;
    font-family: 'terminal grotesque', monospace;
    font-size: 12px;
}
"""

_TOGGLE_BTN = f"""
QPushButton {{
    background-color: #3a3a3a;
    color: #888888;
    border: 1px solid #555;
    font-size: 13px;
}}
QPushButton:checked {{
    background-color: #1a1a1a;
    color: {_ACCENT};
    border: 1px solid {_ACCENT};
}}
QPushButton:hover:!checked {{ background-color: #4a4a4a; }}
"""

_HSLIDER = f"""
QSlider::groove:horizontal {{
    background: #2a2a2a;
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {_ACCENT};
    width: 5px;
    height: 20px;
    margin: -8px 0;
    border-radius: 0px;
}}
QSlider::sub-page:horizontal {{
    background: {_ACCENT};
    border-radius: 2px;
}}
"""

_STROBE_BTN = f"""
QPushButton {{
    background-color: #2a2a2a;
    color: #666666;
    border: 1px solid #555555;
    font-family: 'terminal grotesque', monospace;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}}
QPushButton:hover {{ background-color: #3a3a3a; color: #aaaaaa; }}
QPushButton:pressed {{
    background-color: #2a0a1a;
    color: {_ACCENT};
    border: 1px solid {_ACCENT};
}}
"""

_CUE_BTN = """
QPushButton {
    background-color: #2a2000;
    color: #887700;
    border: 1px solid #554400;
    font-family: 'terminal grotesque', monospace;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}
QPushButton:hover { background-color: #3a3000; color: #bbaa00; }
QPushButton:pressed {
    background-color: #3a2000;
    color: #ffaa00;
    border: 1px solid #ffaa00;
}
"""

_TARGET_BTN = """
QPushButton {
    background-color: #222222;
    color: #666666;
    border: 1px solid #3a3a3a;
    padding: 3px 10px;
    font-family: 'terminal grotesque', monospace;
    font-size: 10px;
    font-weight: bold;
}
QPushButton:checked {
    background-color: #1a4d32;
    color: #4dcc88;
    border: 1px solid #2d7a4f;
}
"""
