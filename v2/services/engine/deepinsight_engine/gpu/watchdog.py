"""Watchdog performa. Ambang seluruhnya dari config."""

from __future__ import annotations

from collections.abc import Callable

from ..core.config import Performance
from .probe import VramProbe


class Watchdog:
    def __init__(
        self,
        performance: Performance,
        probe: VramProbe,
        fps_of: Callable[[], float | None],
        now: Callable[[], float],
    ) -> None:
        self._perf = performance
        self._probe = probe
        self._fps_of = fps_of
        self._now = now
        self._low_fps_since: float | None = None
        self._high_gpu_since: float | None = None
        self.warning: str | None = None
        self.detail: str | None = None

    def tick(self) -> str | None:
        reason = self._fps_reason() or self._vram_reason() or self._gpu_reason()
        self.warning = "GPU-003" if reason else None
        self.detail = reason
        return self.warning

    def _fps_reason(self) -> str | None:
        fps = self._fps_of()
        if fps is None or fps >= self._perf.fps_min:
            self._low_fps_since = None
            return None
        now = self._now()
        self._low_fps_since = now if self._low_fps_since is None else self._low_fps_since
        if now - self._low_fps_since >= self._perf.fps_window_s:
            return "fps"
        return None

    def _vram_reason(self) -> str | None:
        reading = self._probe.snapshot()
        if reading is None or reading.total_mb <= 0:
            return None
        used_pct = 100.0 * reading.used_mb / reading.total_mb
        if used_pct > self._perf.vram_max_pct:
            return "vram"
        return None

    def _gpu_reason(self) -> str | None:
        reading = self._probe.snapshot()
        if reading is None or reading.util_pct <= self._perf.gpu_max_pct:
            self._high_gpu_since = None
            return None
        now = self._now()
        self._high_gpu_since = now if self._high_gpu_since is None else self._high_gpu_since
        if now - self._high_gpu_since >= self._perf.gpu_window_s:
            return "gpu"
        return None
