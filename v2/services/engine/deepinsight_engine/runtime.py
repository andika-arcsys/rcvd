"""Mengikat ring buffer, ModelManager, cache, dan watchdog pada satu sesi engine."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path

from .core.config import Settings
from .core.errors import EngineError
from .core.ids import uuid7
from .diagnostics import LiveStatus, probe_gpu
from .gpu.cache import CacheManager
from .gpu.manager import ModelManager
from .gpu.probe import VramProbe
from .gpu.watchdog import Watchdog
from .video.capture import CaptureLoop
from .video.evidence import store_png
from .video.file_source import open_live, read_file
from .video.frames import RingBuffer, StoredFrame
from .video.marks import store_jpeg
from .video.pipeline import FramePipeline
from .video.quality import configured, turbidity_level
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
        self._lock = threading.RLock()
        self._audit: Callable[[str, str, str, str], None] = _noop_audit
        self._capture = CaptureLoop(self._ingest, settings.thresholds.video.fps)
        self._marks = data_dir / "marks"
        self._uploads = data_dir / "uploads"
        self._vision: dict[str, object] = {}
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
            hydro=settings.hydrodetect,
            spatial=settings.spatialsight,
        )
        self.cache = CacheManager(data_dir / "cache", settings.thresholds.cache.max_mb)
        self.pipeline = FramePipeline(
            RingBuffer(settings.thresholds.video.ring_buffer_s),
            settings.thresholds.video,
            self._enhance,
        )
        self.watchdog = Watchdog(perf, probe, self._display_fps, time.monotonic)

    def start(self) -> None:
        from .gpu.tensorflow_mem import enable_memory_growth

        enable_memory_growth()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="di-watchdog", daemon=True)
        self._thread.start()
        self._open_configured_source()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
        self._capture.stop()
        self.models.close()

    def bind_audit(self, audit: Callable[[str, str, str, str], None]) -> None:
        self._audit = audit

    def poll(self) -> None:
        with self._lock:
            lost = self.pipeline.observe(time.monotonic())
        if lost and lost != self._lost:
            self._on_error(lost, "sinyal video")
        self._lost = lost
        warning = self.watchdog.tick()
        if warning and warning != self._sent_warning:
            self._on_error(warning, self.watchdog.detail)
            self._audit("performance_warning", "watchdog", warning, self.watchdog.detail or "")
        self._sent_warning = warning

    def status(self) -> LiveStatus:
        now = time.monotonic()
        with self._lock:
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

    def save_upload(self, suffix: str, payload: bytes) -> Path:
        self._uploads.mkdir(parents=True, exist_ok=True)
        target = self._uploads / f"{uuid7()}{suffix}"
        target.write_bytes(payload)
        return target

    def open_device(
        self,
        kind: str,
        path: str | None = None,
        device_index: int | None = None,
        rtsp_url: str | None = None,
    ) -> None:
        capture = open_live(kind, path, device_index, rtsp_url)
        with self._lock:
            if self.pipeline.state == "not_configured":
                self.pipeline.state = "connecting"
        self._capture.start(capture)

    def freeze(self, frame_id: str, session: str) -> dict[str, object]:
        with self._lock:
            self._reject_lost(frame_id)
            frame = self.pipeline.ring.get(frame_id)
            if frame is None:
                raise EngineError("VID-002", frame_id)
            if not (self._evidence / f"{frame.frame_id}.png").is_file():
                self._serial += 1
            preset = self.models.preset_name if self.models.active == "aquaclear" else None
            return store_png(self._evidence, frame, session, max(self._serial, 1), preset)

    def mark(self, frame_id: str) -> tuple[str, str]:
        with self._lock:
            self._reject_lost(frame_id)
            frame = self.pipeline.ring.get(frame_id)
        if frame is None:
            raise EngineError("VID-002", frame_id)
        video = self._settings.thresholds.video
        path, digest = store_jpeg(
            self._marks, frame, video.display_max_side, video.display_jpeg_quality
        )
        return str(path), digest

    def video_view(self) -> dict[str, object]:
        with self._lock:
            shown = self.pipeline.last_display
            frame = self.pipeline.ring.latest()
            state = self.pipeline.state
            count = len(self.pipeline.ring)
            fps = self.pipeline.fps("display", time.monotonic())
            serial = self._serial
            warning = self.watchdog.warning
            detail = self.watchdog.detail
        level = turbidity_level(frame, self._settings.video.turbidity) if frame else None
        gpu = probe_gpu()
        return {
            "state": state,
            "frame_id": None if shown is None else shown.frame_id,
            "frame_count": count,
            "enhanced": bool(shown and shown.enhanced),
            "fps": fps,
            "recording": self._settings.video.recording.enabled,
            "turbidity_level": level,
            "turbidity_configured": configured(self._settings.video.turbidity),
            "gpu_util_pct": gpu.utilization_pct,
            "lost": state == "lost",
            "snapshot_count": serial,
            "performance_warning": warning,
            "performance_detail": detail,
        }

    def performance_view(self) -> dict[str, object]:
        info = probe_gpu()
        with self._lock:
            fps = self.pipeline.fps("display", time.monotonic())
        return {
            "warning": self.watchdog.warning,
            "detail": self.watchdog.detail,
            "fps": fps,
            "gpu_util_pct": info.utilization_pct,
            "vram_used_mb": info.vram_used_mb,
            "vram_total_mb": info.vram_total_mb,
        }

    def vision_view(self) -> dict[str, object]:
        from .gpu.report import assemble_vision

        with self._lock:
            event = dict(self._vision)
            preset = self.models.preset_name
        hydro = self._settings.hydrodetect
        spatial = self._settings.spatialsight
        return assemble_vision(event, preset, hydro, spatial)

    def compare_view(self) -> dict[str, object]:
        from .video.compare import compare_payload

        video = self._settings.thresholds.video
        with self._lock:
            frame = self.pipeline.ring.latest()
            shown = self.pipeline.last_display
        jpeg = None if shown is None else shown.jpeg
        return compare_payload(frame, jpeg, video.display_max_side, video.display_jpeg_quality)

    def display_packet(self) -> tuple[dict[str, object], bytes | None]:
        with self._lock:
            shown = self.pipeline.last_display
            state = self.pipeline.state
        jpeg = None if shown is None or state == "lost" else shown.jpeg
        return {
            "state": state,
            "frame_id": None if shown is None else shown.frame_id,
            "enhanced": bool(shown and shown.enhanced),
        }, jpeg

    def set_models_dir(self, config_dir: Path, configured: str) -> None:
        self.models.set_models_dir(resolve_models_dir(config_dir, configured))

    def close_session(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None
        self._capture.stop()
        self.models.close()
        self.cache.clear()

    def _push_many(self, frames: list[StoredFrame]) -> list[str]:
        ids: list[str] = []
        with self._lock:
            for frame in frames:
                self.pipeline.push(frame)
                self._cache_display(frame)
                ids.append(frame.frame_id)
        return ids

    def _ingest(self, width: int, height: int, raw: bytes) -> None:
        frame = StoredFrame(uuid7(), time.monotonic(), width, height, raw)
        with self._lock:
            self.pipeline.push(frame)
            self._cache_display(frame)

    def _reject_lost(self, frame_id: str) -> None:
        if self.pipeline.state == "lost":
            raise EngineError("VID-001", frame_id)

    def _open_configured_source(self) -> None:
        source = self._settings.video.source
        if source.kind is None:
            return
        try:
            self.open_device(source.kind, source.path, source.device_index, source.rtsp_url)
        except EngineError as exc:
            self._on_error(exc.spec.code, exc.detail)

    def _cache_display(self, frame: StoredFrame) -> None:
        shown = self.pipeline.last_display
        if shown is not None and shown.frame_id == frame.frame_id:
            self.cache.put(f"display/{frame.frame_id}", shown.jpeg)

    def _enhance(self, frame: StoredFrame) -> bytes | None:
        try:
            raw = self.models.infer(frame)
        except EngineError as exc:
            self._on_error(exc.spec.code, exc.detail)
            return None
        event = self.models.last_result
        self._vision = {} if event is None else dict(event)
        return raw

    def _display_fps(self) -> float | None:
        with self._lock:
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


def resolve_models_dir(config_dir: Path, configured: str) -> Path:
    path = Path(configured)
    return path if path.is_absolute() else config_dir.parent / path


def build_runtime(
    settings: Settings,
    config_dir: Path,
    data_dir: Path,
    on_error: Callable[[str, str | None], None],
) -> Runtime:
    models_dir = resolve_models_dir(config_dir, settings.app.models.dir)
    return Runtime(settings, models_dir, data_dir, on_error, VramProbe())


def _noop_audit(action: str, entity: str, entity_id: str, detail: str) -> None:
    del action, entity, entity_id, detail


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
