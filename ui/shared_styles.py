from PySide6.QtWidgets import QPushButton

from ui.theme import BG_BUTTON, BG_BUTTON_HOVER, BG_BUTTON_ACTIVE, BORDER

# ── Vertical scrollbar (used by Timeline and BankWidget) ──────────────────────

_SCROLLBAR_V = """
QScrollBar:vertical {
    background: #2a2a2a; width: 14px; border: none; margin: 0;
}
QScrollBar::handle:vertical {
    background: #666666; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #888888; }
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical   { height: 0; border: none; background: none; }
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical   { background: #2a2a2a; }
QScrollBar::up-arrow:vertical,
QScrollBar::down-arrow:vertical { image: none; }
"""

# ── Generic button template + factory ────────────────────────────────────────

_BTN = f"""
QPushButton {{{{
    background-color: {{bg}};
    color: {{fg}};
    border: 1px solid {{border}};
    font-family: 'terminal grotesque', monospace;
    font-weight: bold;
    font-size: {{size}}px;
    padding: {{pad}};
}}}}
QPushButton:hover {{{{ background-color: {{hover}}; }}}}
QPushButton:checked {{{{ background-color: {BG_BUTTON_ACTIVE}; border-color: #aaaaaa; }}}}
"""


def _btn(text: str, bg: str = BG_BUTTON, fg: str = "white", border: str = BORDER,
         size: int = 12, pad: str = "6px 10px", hover: str = BG_BUTTON_HOVER,
         checkable: bool = False) -> QPushButton:
    b = QPushButton(text)
    b.setCheckable(checkable)
    b.setStyleSheet(_BTN.format(bg=bg, fg=fg, border=border,
                                size=size, pad=pad, hover=hover))
    return b
