# Pre-release audit — SendPix3

Status legend: ✅ fixed — ⏳ pending

---

## BUGS

| # | Status | File | Description |
|---|--------|------|-------------|
| 1 | ✅ | `ui/mixette/main_tools.py` | `_on_toggled` copy-pasted identically in `RGBPanel` and `HSVPanel`. Extracted to `_MidiPanel` base class. |
| 2 | ✅ | `engine/render_engine.py` | `_w` and `_h` written by main thread / read by render thread with no lock. Replaced with atomic `_resolution` tuple. |
| 3 | ⏳ | `ui/output_window.py` | Frame assignment from render thread is not atomic. Comment claims "GIL makes this atomic" — it doesn't for numpy array data. Use a `queue.SimpleQueue` or a lock. |
| 4 | ⏳ | `ui/edit/export_widget.py` | `_do_export` calls `self._frames_fn()` live. If user edits during export, frames can be inconsistent mid-save. Snapshot the list at the start of `_do_export`. |
| 5 | ✅ | `ui/live/bank_widget.py` | Hover-out correctly stops the timer via `_on_hover(None)`. Added the same call at the top of `_rebuild_content()` so that a scan/refresh while hovering also stops the timer and clears the stale `_preview_anim`. |
| 27 | ✅ | `engine/render_engine.py` | **CRASH PATH** — `self._strobe_buf` is checked for None then immediately used in `self._strobe_buf[:] = ...` with no local snapshot. `set_strobe_color()` on the main thread can set it to `None` between those two lines → `AttributeError`. Fixed: `buf = self._strobe_buf; buf[:] = ...`. |
| 28 | ✅ | `engine/deck.py` + `ui/live/live_tab.py` | **DATA RACE** — `deck.load()` called from main thread while render thread may be mid-`tick()`. Fixed: `load()` now nulls `_animation` first (making `tick()` return None during the swap), resets all state, then installs the new animation last. `tick()` now snapshots `_paused` and `_cueing` as locals to reduce the inter-read race window. |
| 29 | ✅ | `engine/deck.py` | **THREAD RACE** — `tick()` evaluated `if self._paused and not self._cueing:` as two separate attribute reads. Fixed: both flags are snapshotted as locals at the top of the critical block (subsumed into #28 fix). |
| 30 | ✅ | `ui/main_window.py` | **MIDI STROBE polarity inverted** — was `v < 0.5`, now `v > 0.5` to match all other momentary controls. |
| 31 | ✅ | `ui/main_window.py` | **MIDI TOGGLE_HUE polarity inverted** — was `v < 0.5`, now `v > 0.5`. |
| 32 | ⏳ | `engine/deck.py` | **Frame 0 never played at high FPS** — at animation FPS ≈ ENGINE_FPS, `accumulator` may exceed `frame_dur` on the very first tick, causing `_frame_index` to advance to 1 before frame 0 is ever rendered. Only observable at ≥ 60fps animations. Low priority. |
| 33 | ✅ | `engine/deck.py` | **`unload()` left stale `_last_frame`** — after `unload()`, render engine kept emitting the old array to the preview; "— no content —" was never restored. Fixed: `unload()` now also sets `self._last_frame = None`. |
| 34 | ⏳ | `engine/render_engine.py` | **Blend mode B reads already-mutated `fa`** — `blend_a(fa, fb)` overwrites `fa`; `blend_b(fb, fa)` then receives the pre-blended frame as its secondary input. Asymmetric, order-dependent blending not reflected in the UI. Fix: capture `fa_orig` before applying blend_a. |
| 35 | ✅ | `ui/live/live_tab.py` | **FPS slider initial value never pushed to engine** — only `valueChanged` was connected; initial slider value was never sent. Fixed: explicit `re.deck_a.set_fps(slider.value())` calls added after wiring. |
| 36 | ⏳ | `ui/main_window.py` | **GUI strobe dials not wired to `_midi_strobe` shadow** — `_midi_strobe` is only updated by incoming MIDI. If the user sets strobe color via the `LiveTab` dials and a MIDI `STROBE_R/G/B` message then arrives, the engine snaps back to stale MIDI-side values. Fix: connect `LiveTab` strobe dials to update `_midi_strobe` the same way `rgb_changed` updates `_midi_rgb`. |

---

## INCOHERENCIES

| # | Status | File | Description |
|---|--------|------|-------------|
| 6 | ⏳ | `ui/mixette/mixette_tab.py` + `ui/keybind.py` | MIDI learn shows "waiting…", keybind shows "Press key…". Should be consistent across both flows. |
| 7 | ✅ | multiple | Deck side always a raw string `"A"` / `"B"` in 10+ places. Defined `SIDE_A = "A"`, `SIDE_B = "B"` in `engine/constants.py`. Updated 6 files. |
| 8 | ✅ | `ui/main_window.py` | 20-branch `if/elif` in `_on_midi_value`. Replaced with `_midi_callbacks` registry dict. |
| 9 | ⏳ | `engine/render_engine.py` line 16 | `hue / 2.0` magic constant converting 0–360° to OpenCV 0–180°. Should be a named constant. |
| 10 | ⏳ | `config.py` | Config keys mix suffixes inconsistently: `"animations_folder"`, `"midi_device"`, `"midi_bindings"`, `"key_bindings"`. Worth normalising before the schema grows. |
| 11 | ✅ | `ui/main_window.py` | MIDI value mappings scattered. Extracted to `_midi_range(v, lo, hi)` helper. |
| 37 | ⏳ | `ui/keybind.py` | **CUE actions absent from all registries** — `DECK_A_CUE` and `DECK_B_CUE` are hardcoded in `_make_deck_section`, bypassing the registry pattern every other action uses. Excluded from any future registry-driven feature (conflict detection, reset-all, etc.). |
| 38 | ⏳ | `ui/keybind.py` | **`NEXT_FRAME_2` / `PREV_FRAME_2` misleading names** — these map to `play_forward` / `play_backward` (jog/shuttle), not a secondary frame-step. Any future developer will assume frame-step semantics from the name. Rename to `JOG_FORWARD` / `JOG_BACKWARD` or similar. |
| 45 | ⏳ | `ui/edit/edit_tab.py` | **Tool button labels hardcoded as "B", "G", "I"** — display the default keybind letter but won't update if the user rebinds the tools to different keys in Mixette. |

---

## DEAD CODE

| # | Status | File | Description |
|---|--------|------|-------------|
| 12 | ⏳ | `output/udp_output.py` | `Slot` imported but unused. |
| 13 | ⏳ | `engine/render_engine.py` | `self._tick` incremented every frame, never read anywhere. |
| 14 | ⏳ | `engine/video.py` lines 78–79 | `if target == self._current_idx: pass` is a no-op branch. |
| 15 | ⏳ | `engine/deck.py` | `_has_fps_native` is now cached at `load()` (improvement from previous audit), but if every loadable type always has `fps_native`, the flag is always True and the branch is effectively dead. Confirm whether a non-fps-native animation can ever be loaded; if not, remove the guard entirely. |
| 39 | ⏳ | `engine/deck.py` | **`has_animation` property defined but never called** — no file reads `deck.has_animation`. Either use it or remove it. |
| 47 | ✅ | `ui/edit/canvas.py` | **`set_onion_frame()` method never called** — orphaned method. Removed. |

---

## CODE DUPLICATES

| # | Status | File | Description |
|---|--------|------|-------------|
| 16 | ✅ | `ui/edit/timeline.py` + `ui/live/bank_widget.py` | Identical scrollbar CSS duplicated. Extracted to `_SCROLLBAR_V` in `ui/shared_styles.py`. |
| 17 | ✅ | `ui/live/bank_items.py` + `ui/live/bank_widget.py` + `ui/live/deck_preview.py` | Three separate frame-to-QPixmap implementations. Extracted to `frame_to_pixmap()` in `ui/shared_widgets.py`. |
| 18 | ⏳ | `ui/live/live_tab.py` + `ui/mixette/mixette_tab.py` | Strobe color dials created in both tabs. Mixette ones are permanently disabled (display-only) with no sync to the live values — misleading. See also #40. |
| 19 | ✅ | multiple | Button style templates defined independently in 5 files. Moved generic `_btn` factory to `ui/shared_styles.py`. |

---

## SCALING PROBLEMS

| # | Status | File | Description |
|---|--------|------|-------------|
| 20 | ⏳ | `ui/live/bank_widget.py` | Animation bank loads everything into memory at scan time. No lazy loading, no virtual scroll. Will be slow with large libraries. |
| 21 | ⏳ | `ui/edit/tools.py` + `ui/edit/edit_tab.py` + `ui/keybind.py` + `ui/main_window.py` | Adding a new draw tool requires editing 4 files (tool logic, UI button, action + registry, callback registration). No single registration point. |
| 22 | ⏳ | `engine/deck.py` | No `Protocol` / `ABC` for the animation duck-type. Missing a method gives a runtime `AttributeError` instead of a static error. |
| 23 | ✅ | `ui/main_window.py` | `_first_launch_settings` and `open_settings` almost identical — diverged once already. Merged into `_run_settings_dialog(force_resolution)`. |
| 40 | ⏳ | `engine/render_engine.py` | **Active-play frames re-resized every tick even when frame index didn't advance** — when a deck plays at 5 fps, the same source frame goes through `resize_frame` 60 times/s. The `_frozen_prev_*` cache only helps when paused. Fix: track last-emitted `_frame_index` per deck; skip resize when index unchanged. |
| 41 | ⏳ | `ui/output_window.py` | **`np.repeat` double-upscale + `QImage.copy()` at 60 Hz on the main thread** — two heap allocations plus a full-frame Qt deep copy per timer tick. At 21×16 this is fine; at 100×100 with scale=4 this becomes ~1.3 GB/s allocation on the GUI thread. Replace with `cv2.resize(INTER_NEAREST)` into a pre-allocated buffer, or delegate upscaling to Qt's own `scaled()`. |
| 42 | ⏳ | `engine/render_engine.py` | **`deck_a/b_ready` signals emitted 60×/s even when frozen frame hasn't changed** — preview widget receives 60 queued signal deliveries per second with identical pixel data when a deck is paused. Add a change-detection guard: only emit when `_frozen_prev_*` identity changes. |

---

## NOT URGENT

| # | Status | File | Description |
|---|--------|------|-------------|
| 24 | ⏳ | multiple | Debug `print("[MIDI] ...")` calls mixed into production code. Route through Python `logging` so they can be silenced in release builds. |
| 25 | ⏳ | `config.py` | No schema version key. Add `"version": 1` — costs nothing now, saves migration pain later. |
| 26 | ⏳ | project root | `venv` (macOS) and `venv_windows` both present. macOS venv should be gitignored or excluded from the Windows build. |
| 43 | ⏳ | `ui/mixette/mixette_tab.py` | Strobe color dials, STROBE FREQ slider, and STROBE button in the GLOBAL CONTROLS tab are all `setEnabled(False)` with no re-enable path. They display default/decorative values and cannot be interacted with. Either wire them (two-way sync with LiveTab) or remove them from the Mixette panel entirely. |
