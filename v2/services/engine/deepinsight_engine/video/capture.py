"""Benang pembaca kamera, RTSP, atau berkas ke pemanggil frame."""

from __future__ import annotations

import sys
import threading
from collections.abc import Callable
from typing import Any

from .file_source import read_one


class CaptureLoop:
    def __init__(self, push: Callable[[int, int, bytes], None], fps: int) -> None:
        self._push = push
        self._interval = 1.0 / max(1, fps)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._capture: Any = None

    def start(self, capture: Any) -> None:
        self.stop()
        self._stop = threading.Event()
        self._capture = capture
        self._thread = threading.Thread(target=self._loop, name="di-video", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1)
        self._thread = None
        capture = self._capture
        self._capture = None
        if capture is not None:
            capture.release()

    def _loop(self) -> None:
        while not self._stop.is_set():
            sample = read_one(self._capture)
            if sample is None:
                if self._stop.wait(self._interval):
                    return
                continue
            try:
                self._push(*sample)
            except Exception as exc:  # noqa: BLE001 - satu frame buruk tidak mematikan pembaca
                sys.stderr.write(f"Frame video dilewati: {exc}\n")
                sys.stderr.flush()
            if self._stop.wait(self._interval):
                return
