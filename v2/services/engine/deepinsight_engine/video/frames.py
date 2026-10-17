"""Frame tersimpan dan ring buffer berdurasi tetap."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class StoredFrame:
    frame_id: str
    captured_at: float
    width: int
    height: int
    bgr: bytes


class RingBuffer:
    """Menyimpan frame selama `duration_s`. Yang lebih tua dibuang saat frame baru masuk."""

    def __init__(self, duration_s: float) -> None:
        self._duration = duration_s
        self._frames: deque[StoredFrame] = deque()

    def __len__(self) -> int:
        return len(self._frames)

    def push(self, frame: StoredFrame) -> None:
        self._frames.append(frame)
        newest = frame.captured_at
        while self._frames and newest - self._frames[0].captured_at > self._duration:
            self._frames.popleft()

    def get(self, frame_id: str) -> StoredFrame | None:
        for frame in self._frames:
            if frame.frame_id == frame_id:
                return frame
        return None

    def latest(self) -> StoredFrame | None:
        return self._frames[-1] if self._frames else None
