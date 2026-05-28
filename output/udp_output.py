import socket
import queue
import time
import numpy as np
from PySide6.QtCore import QThread, Signal, Slot

from engine.resize import resize_frame


class UDPOutput(QThread):
    """
    Output thread : downscales the mixed frame to LED resolution and broadcasts UDP.
    Reads frames from an internal queue fed by RenderEngine via Qt signal.
    Never freezes : if no new frame, repeats the last one.
    """
    fps_updated = Signal(float)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self._queue: queue.Queue = queue.Queue(maxsize=2)
        self._running = False
        self._broadcasting = False
        self._last_frame: np.ndarray | None = None

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    @Slot(object)
    def enqueue_frame(self, frame: np.ndarray):
        """Called from RenderEngine thread via DirectConnection — queue.Queue is thread-safe."""
        try:
            self._queue.put_nowait(frame)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(frame)
            except queue.Full:
                pass

    def set_broadcasting(self, enabled: bool):
        self._broadcasting = enabled

    def run(self):
        self._running = True
        timings: list[float] = []

        while self._running:
            t0 = time.perf_counter()

            try:
                frame = self._queue.get(timeout=0.05)
                self._last_frame = frame
            except queue.Empty:
                frame = self._last_frame

            if frame is not None and self._broadcasting:
                self._send_frame(frame)

            elapsed = time.perf_counter() - t0
            timings.append(elapsed)
            if len(timings) > 60:
                timings.pop(0)
                avg = sum(timings) / len(timings)
                if avg > 0:
                    self.fps_updated.emit(1.0 / avg)

    def _send_frame(self, frame: np.ndarray):
        res = self.config.get("led_resolution", [21, 16])
        tw, th = int(res[0]), int(res[1])

        frame = resize_frame(frame, tw, th, "AREA")
        clipped = np.clip(frame, 0, 254).astype(np.uint8)

        try:
            addr = self.config.get("udp_address", "255.255.255.255")
            port = int(self.config.get("udp_port", 37020))
            self._sock.sendto(clipped.tobytes(), (addr, port))
        except Exception:
            pass

    def stop(self):
        self._running = False
        try:
            self._sock.close()
        except Exception:
            pass
