import time

from PySide6.QtCore import QThread, Signal


def get_midi_ports() -> list[str]:
    """Return available MIDI input port names, or [] if rtmidi is not installed."""
    try:
        import rtmidi
        return rtmidi.MidiIn().get_ports()
    except Exception:
        return []


class MidiManager(QThread):
    """
    Background thread that polls a MIDI input port and dispatches normalized
    values (0.0–1.0) via the midi_value signal (thread-safe, queued connection).

    Learn flow:
      start_learn("CONTROL") → the next CC or NoteOn is bound to that control
                                and saved to config["midi_bindings"].
      start_learn("")         → cancel pending learn.

    Control names match the strings emitted by midi_learn_requested in the UI:
      "RED", "GREEN", "BLUE"       — RGB multipliers
      "HUE", "SATURATION", "VALUE" — HSV modifiers
      "STROBE_R/G/B", "STROBE_FREQ", "STROBE"  — strobe controls
      "CROSSFADER", "FPS_A", "FPS_B", "BLEND_A", "BLEND_B" — live controls
    """

    midi_value  = Signal(str, float)   # control_name, value 0.0–1.0
    learn_bound = Signal(str, str)     # control_name, midi_key ("CC_7", "NOTE_36")

    def __init__(self, config):
        super().__init__()
        self._config        = config
        self._running       = False
        self._port          = None
        self._learn_target: str = ""
        self._bindings: dict[str, str] = {}   # control → midi_key
        self._reverse:  dict[str, str] = {}   # midi_key → control
        self._load_bindings()

    # ── Public API ─────────────────────────────────────────────────────────────

    def start_learn(self, control_name: str) -> None:
        self._learn_target = control_name

    def open_device(self, device_name: str) -> None:
        self._close_port()
        if not device_name:
            #print("[MIDI] open_device: no device name, skipping")
            return
        try:
            import rtmidi
            midi_in = rtmidi.MidiIn()
            ports = midi_in.get_ports()
            #print(f"[MIDI] available ports: {ports}")
            #print(f"[MIDI] looking for: '{device_name}'")
            for i, name in enumerate(ports):
                if name == device_name:
                    midi_in.set_callback(self._midi_callback)
                    midi_in.open_port(i)
                    midi_in.ignore_types(sysex=True, timing=True, active_sense=True)
                    self._port = midi_in
                    #print(f"[MIDI] opened port {i}: '{name}' (callback mode)")
                    return
            #print(f"[MIDI] port not found!")
        except Exception as e:
            print(f"[MIDI] open_device error: {e}")

    # ── Thread — kept alive so QThread lifetime matches the app ───────────────

    def run(self):
        self._running = True
        while self._running:
            time.sleep(0.05)

    def stop(self):
        self._running = False
        self._close_port()

    # ── Internal ───────────────────────────────────────────────────────────────

    def _load_bindings(self):
        saved = self._config.get("midi_bindings", {})
        self._bindings = dict(saved)
        self._reverse  = {v: k for k, v in saved.items()}

    def _save_bindings(self):
        self._config.set("midi_bindings", dict(self._bindings))

    def _close_port(self):
        if self._port is not None:
            try:
                self._port.cancel_callback()
                self._port.close_port()
            except Exception:
                pass
            self._port = None

    def _midi_callback(self, message, data=None):
        raw = message[0]
        #print(f"[MIDI] callback raw: {raw}")
        self._dispatch(raw)

    def _dispatch(self, data: list[int]) -> None:
        if len(data) < 3:
            return
        status = data[0] & 0xF0

        if status == 0xB0:                           # CC
            midi_key = f"CC_{data[1]}"
            norm_val = data[2] / 127.0
        elif status == 0x90:                         # Note On (vel=0 → Note Off)
            midi_key = f"NOTE_{data[1]}"
            norm_val = 1.0 if data[2] > 0 else 0.0
        elif status == 0x80:                         # Note Off
            midi_key = f"NOTE_{data[1]}"
            norm_val = 0.0
        else:
            return

        if self._learn_target:
            old_key = self._bindings.get(self._learn_target)
            if old_key:
                self._reverse.pop(old_key, None)
            self._bindings[self._learn_target] = midi_key
            self._reverse[midi_key] = self._learn_target
            self.learn_bound.emit(self._learn_target, midi_key)
            self._learn_target = ""
            self._save_bindings()
            return

        control = self._reverse.get(midi_key)
        if control:
            self.midi_value.emit(control, norm_val)
