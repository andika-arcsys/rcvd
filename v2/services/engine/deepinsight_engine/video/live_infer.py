"""Inferensi GPU di luar jalur gambar.

Gambar kamera tetap jalan. Hanya frame terbaru yang masuk GPU.
Hasil model yang sudah diganti tidak ditulis kembali.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from .frames import StoredFrame


class LiveInfer:
    def __init__(self, run: Callable[[StoredFrame, int], None]) -> None:
        self._run = run
        self._cv = threading.Condition()
        self._pending: StoredFrame | None = None
        self._started = False
        self._generation = 0

    def submit(self, frame: StoredFrame) -> None:
        with self._cv:
            self._pending = frame
            if not self._started:
                self._started = True
                threading.Thread(target=self._loop, name="di-live-infer", daemon=True).start()
            self._cv.notify()

    def cancel(self) -> None:
        """Batalkan hasil yang masih di GPU. Frame kamera tidak dihapus."""
        with self._cv:
            self._generation += 1
            self._pending = None
            self._cv.notify()

    def accepts(self, generation: int) -> bool:
        with self._cv:
            return generation == self._generation

    def _loop(self) -> None:
        while True:
            with self._cv:
                while self._pending is None:
                    self._cv.wait()
                frame = self._pending
                self._pending = None
                generation = self._generation
            try:
                self._run(frame, generation)
            except Exception:  # noqa: BLE001 - satu frame gagal, kamera dan frame berikut tetap jalan
                with self._cv:
                    if self._pending is None:
                        self._started = False
                        return
                continue


def publish_allowed(active: str | None, kind: str | None, state: str) -> bool:
    """Hasil hanya masuk bila model yang menghasilkan masih yang aktif."""
    return state == "ready" and active is not None and active == kind
