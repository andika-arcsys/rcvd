"""Pengumpul data /diagnostics: GPU, disk, cache, versi, error terakhir."""

from __future__ import annotations

import importlib
import platform
import shutil
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from . import __version__
from .core.config import Settings


class GpuInfo(BaseModel):
    available: bool
    name: str | None = None
    vram_total_mb: float | None = None
    vram_used_mb: float | None = None
    utilization_pct: float | None = None
    error_code: str | None = None
    note: str | None = None


class DiskInfo(BaseModel):
    path: str
    free_gb: float
    total_gb: float


class CacheInfo(BaseModel):
    path: str
    size_mb: float
    max_mb: int


class ModelInfo(BaseModel):
    active: str | None
    state: str


class VideoInfo(BaseModel):
    state: str
    fps_display: float | None = None
    fps_inference: float | None = None
    ring_buffer_s: float
    frame_count: int = 0


class LastError(BaseModel):
    ts: float
    code: str
    detail: str | None = None


class DiagnosticsReport(BaseModel):
    app_name: str
    app_version: str
    engine_version: str
    env: str
    session_id: str
    uptime_s: float
    python: str
    platform: str
    gpu: GpuInfo
    model: ModelInfo
    video: VideoInfo
    camera_state: str
    clock_sync: str
    clock_utc: str
    cache: CacheInfo
    disk: DiskInfo
    workers: int
    last_errors: list[LastError]
    performance_warning: str | None = None
    performance_detail: str | None = None


@dataclass
class ErrorLog:
    """Jejak 20 error terakhir untuk /diagnostics."""

    items: deque[LastError] = field(default_factory=lambda: deque(maxlen=20))

    def add(self, code: str, detail: str | None) -> None:
        self.items.append(LastError(ts=time.time(), code=code, detail=detail))


def probe_gpu() -> GpuInfo:
    """Baca GPU lewat NVML bila ada. Tanpa GPU: tersedia=false dengan kode GPU-001."""
    try:
        nvml: Any = importlib.import_module("pynvml")
        nvml.nvmlInit()
        try:
            handle = nvml.nvmlDeviceGetHandleByIndex(0)
            mem = nvml.nvmlDeviceGetMemoryInfo(handle)
            util = nvml.nvmlDeviceGetUtilizationRates(handle)
            raw_name = nvml.nvmlDeviceGetName(handle)
            name = raw_name.decode() if isinstance(raw_name, bytes) else str(raw_name)
            return GpuInfo(
                available=True,
                name=name,
                vram_total_mb=mem.total / 1024**2,
                vram_used_mb=mem.used / 1024**2,
                utilization_pct=float(util.gpu),
            )
        finally:
            nvml.nvmlShutdown()
    except ImportError:
        return GpuInfo(
            available=False, error_code="GPU-001", note="Paket nvidia-ml-py belum dipasang."
        )
    except Exception as exc:  # noqa: BLE001 - NVML melempar bermacam error; dicatat, bukan ditelan
        return GpuInfo(available=False, error_code="GPU-001", note=f"NVML gagal: {exc}")


def _dir_size_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / 1024**2


class LiveStatus(BaseModel):
    model_active: str | None
    model_state: str
    workers: int
    video_state: str
    fps_display: float | None = None
    fps_inference: float | None = None
    frame_count: int = 0
    cache_mb: float = 0.0
    performance_warning: str | None = None
    performance_detail: str | None = None


def camera_state_for(video_state: str | None) -> str:
    """Sumber yang sudah dibuka, hidup, atau putus tetap terhitung terhubung."""
    if video_state in {"connecting", "live", "lost"}:
        return "connected"
    return "not_configured"


def build_report(
    settings: Settings,
    data_dir: Path,
    session_id: str,
    started: float,
    errors: ErrorLog,
    live: LiveStatus | None = None,
) -> DiagnosticsReport:
    disk = shutil.disk_usage(data_dir if data_dir.exists() else data_dir.anchor or ".")
    cache_dir = data_dir / "cache"
    return DiagnosticsReport(
        app_name=settings.app.app.name,
        app_version=settings.app.app.version,
        engine_version=__version__,
        env=settings.app.app.env,
        session_id=session_id,
        uptime_s=round(time.monotonic() - started, 3),
        python=platform.python_version(),
        platform=platform.platform(),
        gpu=probe_gpu(),
        model=ModelInfo(
            active=None if live is None else live.model_active,
            state="optical" if live is None else live.model_state,
        ),
        video=VideoInfo(
            state="not_configured" if live is None else live.video_state,
            fps_display=None if live is None else live.fps_display,
            fps_inference=None if live is None else live.fps_inference,
            ring_buffer_s=settings.thresholds.video.ring_buffer_s,
            frame_count=0 if live is None else live.frame_count,
        ),
        camera_state=camera_state_for(None if live is None else live.video_state),
        # Jam OS. NTP tidak dicek (Q-UI-5); clock_sync=ok berarti jam sistem terbaca.
        clock_sync="ok",
        clock_utc=datetime.now(UTC).isoformat(),
        cache=CacheInfo(
            path=str(cache_dir),
            size_mb=round(_dir_size_mb(cache_dir) if live is None else live.cache_mb, 3),
            max_mb=settings.thresholds.cache.max_mb,
        ),
        disk=DiskInfo(
            path=str(data_dir),
            free_gb=round(disk.free / 1024**3, 2),
            total_gb=round(disk.total / 1024**3, 2),
        ),
        workers=0 if live is None else live.workers,
        last_errors=list(errors.items),
        performance_warning=None if live is None else live.performance_warning,
        performance_detail=None if live is None else live.performance_detail,
    )
