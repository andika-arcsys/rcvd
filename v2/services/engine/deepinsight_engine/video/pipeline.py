"""Mendorong frame ke ring buffer dan menyiapkan JPEG tampilan."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from ..core.config import Video
from .encode import encode_jpeg
from .frames import RingBuffer, StoredFrame


@dataclass
class DisplayFrame:
    frame_id: str
    jpeg: bytes
    enhanced: bool


class FramePipeline:
    def __init__(
        self,
        ring: RingBuffer,
        video: Video,
        enhancer: Callable[[StoredFrame], bytes | None],
    ) -> None:
        self.ring = ring
        self._video = video
        self._enhancer = enhancer
        self.state = "not_configured"
        self.last_at: float | None = None
        self.last_display: DisplayFrame | None = None
        self._display_times: deque[float] = deque()
        self._infer_times: deque[float] = deque()

    def push(self, frame: StoredFrame) -> None:
        self.state = "live"
        self.last_at = frame.captured_at
        self.ring.push(frame)
        self._remember(self._display_times, frame.captured_at)
        enhanced = self._enhancer(frame)
        shown = enhanced if enhanced is not None else frame.bgr
        if enhanced is not None:
            self._remember(self._infer_times, frame.captured_at)
        self.last_display = DisplayFrame(
            frame.frame_id,
            encode_jpeg(
                shown,
                frame.width,
                frame.height,
                self._video.display_max_side,
                self._video.display_jpeg_quality,
            ),
            enhanced is not None,
        )

    def observe(self, now: float) -> str | None:
        if self.state != "live" or self.last_at is None:
            return None
        if now - self.last_at > self._video.lost_signal_s:
            self.state = "lost"
            return "VID-001"
        return None

    def fps(self, kind: str, now: float) -> float | None:
        if self.state != "live":
            return None
        times = self._infer_times if kind == "infer" else self._display_times
        self._trim(times, now)
        return float(len(times))

    def _remember(self, bucket: deque[float], at: float) -> None:
        bucket.append(at)
        self._trim(bucket, at)

    def _trim(self, bucket: deque[float], now: float) -> None:
        window = self._video.fps_sample_s
        while bucket and now - bucket[0] > window:
            bucket.popleft()
