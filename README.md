# ANDRE — SendPix3

Real-time pixel art VJ software for LED matrix installations. Built with Python + PySide6.

---

## Overview

SendPix3 is a dual-mode tool for creating and performing with pixel art animations on LED hardware:

- **EDIT** — frame-by-frame pixel art editor with timeline, color wheel, palette, and live-edit mode
- **LIVE** — real-time mix of two sources (animations or MP4 videos) with crossfader, blend modes, and UDP output to LED panels
- **MIXETTE** — MIDI-controllable color correction (HSV + RGB) with learn mode

Output is broadcast over UDP as a raw RGB byte stream (row-major, clipped to \[0, 254\]).

---

## Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| UI | PySide6 (Qt6) |
| Image processing | NumPy |
| Image loading | Pillow |
| Video decoding | OpenCV (`cv2`) |
| MIDI | python-rtmidi |
| Network | socket (stdlib) |
| Config | JSON (stdlib) |

---

## Installation

```bash
git clone https://github.com/I-blueHand-I/ANDRE.git
cd ANDRE
pip install -r requirements.txt
```

Copy `config.example.json` to `config.json` and set your paths before first launch:

```bash
cp config.example.json config.json
```

```bash
python main.py
```

On first launch a settings dialog will open to configure LED resolution, UDP address, and media folders.

---

## Configuration

`config.json` (gitignored — use `config.example.json` as template):

| Key | Description |
|---|---|
| `led_resolution` | `[width, height]` of the LED matrix |
| `udp_port` | UDP broadcast port (default `37020`) |
| `udp_address` | Broadcast address (default `255.255.255.255`) |
| `animations_folder` | Path to folder of animation sub-folders (PNG sequences) |
| `mp4_folder` | Path to folder of `.mp4` files |
| `midi_device` | MIDI input device name |
| `midi_bindings` | Control → MIDI key mappings (populated via learn mode) |
| `key_bindings` | Action → keyboard shortcut mappings |
| `interpolation` | Resize method for LED output (`NEAREST`, `BICUBIC`, `AREA`, `LINEAR`) |

---

## Animation format

Each animation is a sub-folder of numbered PNG files:

```
animations_folder/
├── my_loop/
│   ├── 000.png
│   ├── 001.png
│   └── ...
└── another_anim/
    └── ...
```

---

## Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Space` | Play / Pause (edit) |
| `←` / `→` | Previous / Next frame |
| `F` | Live Edit → Deck A (toggle) |
| `Ctrl+F` | Live Edit → Deck B (toggle) |
| `T` / `Y` | Play/Pause Deck A / B |
| `R` / `U` | Cue Deck A / B (hold) |
| `S` | Strobe (hold) |
| `H` | Toggle hue |
| `=` | Add frame |
| `Return` | Export animation |
| `Ctrl+S` | Settings |
| `Ctrl+O` | Output window |
| `Ctrl+1/2/3` | Switch tab |

---

## Architecture

Three threads run independently so a UI action never blocks the LED output:

```
UI Thread (PySide6)
    │  Qt Signals
    ▼
Render Thread (QThread) — 60 Hz mix loop
    │  DirectConnection
    ▼
UDP Output Thread (QThread) — broadcast + output window
```

Decks, mixer, and preview all work at native resolution. Downscale to LED resolution happens only in the output thread.

---

## Pending revisions

| # | File | Description |
|---|---|---|
| 3 | `ui/output_window.py` | Frame assignment from render thread is not atomic. Use `queue.SimpleQueue` or a lock. |
| 4 | `ui/edit/export_widget.py` | `_do_export` calls `self._frames_fn()` live — snapshot the list at the start of export. |
| 6 | `ui/mixette/mixette_tab.py` + `ui/keybind.py` | MIDI learn shows "waiting…", keybind shows "Press key…" — inconsistent UX. |
| 9 | `engine/render_engine.py` | `hue / 2.0` magic constant (OpenCV 0–180° range) — should be a named constant. |
| 10 | `config.py` | Config keys mix suffixes inconsistently (`animations_folder`, `midi_device`, `midi_bindings`…). |
| 12 | `output/udp_output.py` | `Slot` imported but unused. |
| 13 | `engine/render_engine.py` | `self._tick` incremented every frame, never read anywhere. |
| 14 | `engine/video.py` | `if target == self._current_idx: pass` is a no-op branch. |
| 15 | `engine/deck.py` | `_has_fps_native` may always be `True` — confirm and remove the guard if so. |
| 18 | `ui/live/live_tab.py` + `ui/mixette/mixette_tab.py` | Strobe color dials duplicated; Mixette ones are disabled with no sync. |
| 20 | `ui/live/bank_widget.py` | Animation bank loads all frames into memory at scan time — no lazy loading or virtual scroll. |
| 21 | `ui/edit/tools.py` + `ui/edit/edit_tab.py` + `ui/keybind.py` | Adding a new draw tool requires editing 3 files — no single registration point. |
| 22 | `engine/deck.py` | No `Protocol` / ABC for the animation duck-type — missing method gives a runtime `AttributeError`. |
| 24 | multiple | Debug `print("[MIDI] …")` calls in production — route through `logging`. |
| 25 | `config.py` | No schema version key — add `"version": 1` before the config grows further. |
| 32 | `engine/deck.py` | Frame 0 never played at high FPS — accumulator may skip it on the first tick at ≥60fps animations. |
| 34 | `engine/render_engine.py` | Blend mode B reads already-mutated `fa` — asymmetric result not reflected in the UI. |
| 36 | `ui/main_window.py` | GUI strobe dials not wired to `_midi_strobe` shadow — MIDI message snaps back to stale values. |
| 37 | `ui/keybind.py` | `DECK_A_CUE` / `DECK_B_CUE` hardcoded, bypassing the action registry. |
| 38 | `ui/keybind.py` | `NEXT_FRAME_2` / `PREV_FRAME_2` are jog actions, not frame-step — misleading names. |
| 39 | `engine/deck.py` | `has_animation` property defined but never called — use it or remove it. |
| 40 | `engine/render_engine.py` | Active-play frames re-resized every tick even when frame index didn't advance. |
| 41 | `ui/output_window.py` | `np.repeat` double-upscale + `QImage.copy()` at 60 Hz — replace with `cv2.resize` into a pre-allocated buffer. |
| 42 | `engine/render_engine.py` | `deck_a/b_ready` signals emitted 60×/s even when paused frame is unchanged. |
| 43 | `ui/mixette/mixette_tab.py` | Strobe dials, freq slider, and strobe button all `setEnabled(False)` with no re-enable path — wire or remove. |
