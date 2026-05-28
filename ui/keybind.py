from typing import NamedTuple

from PySide6.QtWidgets import QApplication, QPushButton, QWidget, QLineEdit
from PySide6.QtCore import Qt, Signal, QObject, QEvent
from PySide6.QtGui import QKeySequence


class Action:
    """Single source of truth for bindable action names (key bindings and MIDI)."""
    STROBE            = "STROBE"
    TOGGLE_HUE        = "TOGGLE_HUE"
    LIVE_EDIT_A       = "LIVE_EDIT_A"
    LIVE_EDIT_B       = "LIVE_EDIT_B"
    DECK_A_PLAY_PAUSE = "DECK_A_PLAY_PAUSE"
    DECK_B_PLAY_PAUSE = "DECK_B_PLAY_PAUSE"
    DECK_A_CUE        = "DECK_A_CUE"
    DECK_B_CUE        = "DECK_B_CUE"
    OUTPUT        = "OUTPUT"
    SETTINGS      = "SETTINGS"
    ADD_FRAME     = "ADD_FRAME"
    ADD_4_FRAMES  = "ADD_4_FRAMES"
    ADD_12_FRAMES = "ADD_12_FRAMES"
    ADD_24_FRAMES = "ADD_24_FRAMES"
    NEW_ANIM      = "NEW_ANIM"
    PLAY_PAUSE    = "PLAY_PAUSE"
    NEXT_FRAME    = "NEXT_FRAME"
    NEXT_FRAME_2  = "NEXT_FRAME_2"
    PREV_FRAME    = "PREV_FRAME"
    PREV_FRAME_2  = "PREV_FRAME_2"
    EXPORT_ANIM   = "EXPORT_ANIM"
    TOOL_BRUSH      = "TOOL_BRUSH"
    TOOL_FILL       = "TOOL_FILL"
    TOOL_EYEDROPPER = "TOOL_EYEDROPPER"
    TOOL_ONION      = "TOOL_ONION"


class ActionDef(NamedTuple):
    name:  str
    label: str
    hold:  bool = False


# COLORS OUTPUT tab in Mixette.
COLORS_REGISTRY: tuple[ActionDef, ...] = (
    ActionDef(Action.TOGGLE_HUE, "TOGGLE HUE"),
)

# GLOBAL CONTROLS right column in Mixette. STROBE has its own custom row.
# To add an action: add it here, then register its callback in main_window.
GLOBAL_RIGHT_REGISTRY: tuple[ActionDef, ...] = (
    ActionDef(Action.OUTPUT,   "OUTPUT"),
    ActionDef(Action.SETTINGS, "SETTINGS"),
)

EDIT_LEFT_REGISTRY: tuple[ActionDef, ...] = (
    ActionDef(Action.ADD_FRAME,    "+1 FRAME"),
    ActionDef(Action.ADD_4_FRAMES,  "+4 FRAMES"),
    ActionDef(Action.ADD_12_FRAMES, "+12 FRAMES"),
    ActionDef(Action.ADD_24_FRAMES, "+24 FRAMES"),
    ActionDef(Action.NEW_ANIM,     "NEW ANIM"),
    ActionDef(Action.LIVE_EDIT_A,  "LIVE EDIT DECK A"),
    ActionDef(Action.LIVE_EDIT_B,  "LIVE EDIT DECK B"),
)

EDIT_TOOLS_REGISTRY: tuple[ActionDef, ...] = (
    ActionDef(Action.TOOL_BRUSH,      "BRUSH"),
    ActionDef(Action.TOOL_FILL,       "FILL"),
    ActionDef(Action.TOOL_EYEDROPPER, "EYEDROPPER"),
    ActionDef(Action.TOOL_ONION,      "ONION SKIN", hold=True),
)

EDIT_RIGHT_REGISTRY: tuple[ActionDef, ...] = (
    ActionDef(Action.PLAY_PAUSE,   "PLAY/PAUSE"),
    ActionDef(Action.NEXT_FRAME,   "NEXT"),
    ActionDef(Action.NEXT_FRAME_2, "FORWARD"),
    ActionDef(Action.PREV_FRAME,   "PREVIOUS"),
    ActionDef(Action.PREV_FRAME_2, "BACKWARD"),
    ActionDef(Action.EXPORT_ANIM,  "EXPORT ANIM"),
)



_STYLE_IDLE = """
QPushButton {
    background-color: #1a1a1a;
    color: #aaaaaa;
    border: 1px solid #444444;
    padding: 3px 10px;
    font-family: 'terminal grotesque', monospace;
    font-size: 11px;
    min-width: 90px;
}
QPushButton:hover { background-color: #2a2a2a; }
"""

_STYLE_CAPTURING = """
QPushButton {
    background-color: #1a1a2a;
    color: #5588ff;
    border: 1px solid #5588ff;
    padding: 3px 10px;
    font-family: 'terminal grotesque', monospace;
    font-size: 11px;
    min-width: 90px;
}
"""


class KeyBindButton(QPushButton):
    """Button that captures a keyboard shortcut when clicked. Emits key_captured(str)."""

    key_captured = Signal(str)  # key sequence string, e.g. "F9", "Ctrl+F1"; "" to clear

    def __init__(self, parent=None):
        super().__init__("—", parent)
        self._capturing = False
        self._key_seq = ""
        self.setStyleSheet(_STYLE_IDLE)
        self.setFocusPolicy(Qt.StrongFocus)
        self.clicked.connect(self._start_capture)

    def set_key(self, key_seq: str):
        self._key_seq = key_seq
        self.setText(key_seq if key_seq else "—")
        self.setStyleSheet(_STYLE_IDLE)

    def _start_capture(self):
        if self._capturing:
            return
        self._capturing = True
        self.setText("Press key…")
        self.setStyleSheet(_STYLE_CAPTURING)
        self.grabKeyboard()

    def _stop_capture(self):
        self._capturing = False
        self.releaseKeyboard()

    def keyPressEvent(self, event):
        if not self._capturing:
            super().keyPressEvent(event)
            return
        key = event.key()
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta, Qt.Key_unknown):
            return
        if key == Qt.Key_Escape:
            self._stop_capture()
            self.set_key(self._key_seq)
            return
        if key in (Qt.Key_Backspace, Qt.Key_Delete):
            self._stop_capture()
            self._key_seq = ""
            self.setText("—")
            self.setStyleSheet(_STYLE_IDLE)
            self.key_captured.emit("")
            return
        seq = QKeySequence(event.keyCombination()).toString()
        self._stop_capture()
        self._key_seq = seq
        self.setText(seq)
        self.setStyleSheet(_STYLE_IDLE)
        self.key_captured.emit(seq)

    def focusOutEvent(self, event):
        if self._capturing:
            self._stop_capture()
            self.set_key(self._key_seq)
        super().focusOutEvent(event)


class KeyBindManager(QObject):
    """Global keyboard shortcut dispatcher. Installs event filter on QApplication."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._actions: dict[str, object] = {}      # action → callable (press)
        self._hold_actions: dict[str, tuple] = {}  # action → (on_press, on_release)
        self._key_map: dict[str, str] = {}         # key_seq → action
        QApplication.instance().installEventFilter(self)

    def register(self, action: str, callback) -> None:
        self._actions[action] = callback
        self._hold_actions.pop(action, None)

    def register_hold(self, action: str, on_press, on_release) -> None:
        self._hold_actions[action] = (on_press, on_release)
        self._actions.pop(action, None)

    def get_bindings(self) -> dict[str, str]:
        """Returns {action_name: key_seq} for all currently bound actions."""
        return {action: key for key, action in self._key_map.items()}

    def update_binding(self, action: str, key_seq: str) -> None:
        self._key_map = {k: a for k, a in self._key_map.items() if a != action}
        if key_seq:
            self._key_map[key_seq] = action

    def eventFilter(self, obj, event) -> bool:
        et = event.type()
        if et not in (QEvent.KeyPress, QEvent.KeyRelease):
            return False
        if event.isAutoRepeat():
            return False
        if QWidget.keyboardGrabber() is not None:
            return False
        if isinstance(QApplication.focusWidget(), QLineEdit):
            return False
        seq = QKeySequence(event.keyCombination()).toString()
        action = self._key_map.get(seq)
        if not action:
            return False
        if et == QEvent.KeyPress:
            if action in self._actions:
                self._actions[action]()
                return True
            if action in self._hold_actions:
                self._hold_actions[action][0]()
                return True
        elif et == QEvent.KeyRelease:
            if action in self._hold_actions:
                self._hold_actions[action][1]()
                return True
        return False
