"""Mengikat ring buffer, ModelManager, cache, dan watchdog pada satu sesi engine."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path

from .core.config import Settings
from .core.errors import EngineError
from .core.ids import uuid7
from .diagnostics import LiveStatus
from .gpu.cache import CacheManager
from .gpu.manager import ModelManager
from .gpu.probe import VramProbe
from .gpu.watchdog import Watchdog
from .video.evidence import store_png
from .video.file_source import read_file, reject_live_device
from .video.frames import RingBuffer, StoredFrame
from .video.pipeline import FramePipeline
from .video.synthetic import gradient_bgr


class Runtime:
    def __init__(
        self,
        settings: Settings,
        models_dir: Path,
        data_dir: Path,
        on_error: Callable[[str, str | None], None],
        probe: VramProbe,
    ) -> None:
        perf = settings.thresholds.performance
        self._settings = settings
        self._on_error = on_error
        self._evidence = data_dir / "evidence"
        self._serial = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lost: str | None = None
        self._sent_warning: str | None = None
        self.models = ModelManager(
            settings.models,
            models_dir,
            settings.aquaclear.presets,
            settings.aquaclear.default,
            probe,
            perf.unload_timeout_s,
            perf.load_timeout_s,
            perf.vram_baseline_tolerance_mb,
            on_error,
        )
        self.cache = CacheManager(data_dir / "cache", settings.thresholds.cache.max_mb)
        self.pipeline = FramePipeline(
            RingBuffer(settings.thresholds.video.ring_buffer_s),
            settings.thresholds.video,
            self._enhance,
        )
        self.watchdog = Watchdog(perf, probe, self._display_fps, time.monotonic)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="di-watchdog", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
        self.models.close()

    def poll(self) -> None:
        lost = self.pipeline.observe(time.monotonic())
        if lost and lost != self._lost:
            self._on_error(lost, "sinyal video")
        self._lost = lost
        warning = self.watchdog.tick()
        if warning and warning != self._sent_warning:
            self._on_error(warning, self.watchdog.detail)
        self._sent_warning = warning

    def status(self) -> LiveStatus:
        now = time.monotonic()
        return LiveStatus(
            model_active=self.models.active,
            model_state=self.models.state,
            workers=self.models.workers,
            video_state=self.pipeline.state,
            fps_display=self.pipeline.fps("display", now),
            fps_inference=self.pipeline.fps("infer", now),
            frame_count=len(self.pipeline.ring),
            cache_mb=self.cache.used_mb(),
            performance_warning=self.watchdog.warning,
            performance_detail=self.watchdog.detail,
        )

    def switch(self, name: str, preset: str | None) -> None:
        self.models.switch(name, preset)

    def push_synthetic(self, count: int, width: int, height: int) -> list[str]:
        self._check_geometry(count, width, height)
        return self._push_many(_synthetic_frames(count, width, height, self._settings))

    def push_file(self, path: Path) -> list[str]:
        video = self._settings.thresholds.video
        frames = read_file(path, video.fps * int(video.ring_buffer_s))
        now = time.monotonic()
        stored = [StoredFrame(uuid7(), now, width, height, bgr) for width, height, bgr in frames]
        return self._push_many(stored)

    def open_device(self, kind: str) -> None:
        reject_live_device(kind)

    def freeze(self, frame_id: str, session: str) -> dict[str, object]:
        frame = self.pipeline.ring.get(frame_id)
        if frame is None:
            raise EngineError("VID-002", frame_id)
        if not (self._evidence / f"{frame.frame_id}.png").is_file():
            self._serial += 1
        return store_png(self._evidence, frame, session, max(self._serial, 1))

    def close_session(self) -> None:
        self.models.close()
        self.cache.clear()

    def _push_many(self, frames: list[StoredFrame]) -> list[str]:
        ids: list[str] = []
        for frame in frames:
            self.pipeline.push(frame)
            self._cache_display(frame)
            ids.append(frame.frame_id)
        return ids

    def _cache_display(self, frame: StoredFrame) -> None:
        shown = self.pipeline.last_display
        if shown is not None and shown.frame_id == frame.frame_id:
            self.cache.put(f"display/{frame.frame_id}", shown.jpeg)

    def _enhance(self, frame: StoredFrame) -> bytes | None:
        try:
            return self.models.infer(frame)
        except EngineError as exc:
            self._on_error(exc.spec.code, exc.detail)
            return None

    def _display_fps(self) -> float | None:
        return self.pipeline.fps("display", time.monotonic())

    def _check_geometry(self, count: int, width: int, height: int) -> None:
        video = self._settings.thresholds.video
        limit = video.fps * int(video.ring_buffer_s)
        if not 1 <= count <= max(1, limit):
            raise EngineError("API-002", "jumlah frame di luar ring buffer")
        if width < 2 or height < 2 or width > video.width or height > video.height:
            raise EngineError("API-002", "ukuran frame di luar config video")

    def _loop(self) -> None:
        interval = self._settings.thresholds.performance.watchdog_interval_s
        while not self._stop.wait(interval):
            self.poll()


def build_runtime(
    settings: Settings,
    config_dir: Path,
    data_dir: Path,
    on_error: Callable[[str, str | None], None],
) -> Runtime:
    configured = Path(settings.app.models.dir)
    models_dir = configured if configured.is_absolute() else config_dir.parent / configured
    return Runtime(settings, models_dir, data_dir, on_error, VramProbe())


def _synthetic_frames(count: int, width: int, height: int, settings: Settings) -> list[StoredFrame]:
    now = time.monotonic()
    step = 1.0 / settings.thresholds.video.fps
    frames: list[StoredFrame] = []
    for index in range(count):
        frames.append(
            StoredFrame(
                uuid7(),
                now - (count - 1 - index) * step,
                width,
                height,
                gradient_bgr(width, height, index),
            )
        )
    return frames
