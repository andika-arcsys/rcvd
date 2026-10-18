"""Profil beban sesi: banyak FREEZE, ganti fitur, lalu ukur RSS dan cache."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import psutil
from fastapi.testclient import TestClient

from .api.app import create_app
from .core.config import load_settings


def frame_size(config_dir: Path) -> tuple[int, int]:
    video = load_settings(config_dir).thresholds.video
    width = min(video.display_max_side, video.width)
    height = max(2, int(video.height * width / video.width))
    return width, height


def profile_session(config_dir: Path, data_dir: Path, freezes: int) -> dict[str, object]:
    started = time.perf_counter()
    app = create_app(config_dir=config_dir, data_dir=data_dir)
    boot_s = round(time.perf_counter() - started, 3)
    width, height = frame_size(config_dir)
    process = psutil.Process()
    with TestClient(app) as client:
        before = process.memory_info().rss
        peak = before
        for _ in range(freezes):
            pushed = client.post(
                "/video/synthetic", json={"count": 1, "width": width, "height": height}
            )
            pushed.raise_for_status()
            frame_id = pushed.json()["frame_ids"][-1]
            frozen = client.post("/freeze", json={"frame_id": frame_id})
            frozen.raise_for_status()
            peak = max(peak, process.memory_info().rss)
        _switch_features(client)
        video = app.state.settings.thresholds.video
        time.sleep(video.ring_buffer_s + 0.05)
        client.post(
            "/video/synthetic", json={"count": 1, "width": width, "height": height}
        ).raise_for_status()
        after = process.memory_info().rss
        report = client.get("/diagnostics").json()
        client.post("/session/close").raise_for_status()
        closed = process.memory_info().rss
        names = [item.name for item in threading.enumerate()]
    growth = 0.0 if before == 0 else (after - before) / before
    return {
        "freezes": freezes,
        "width": width,
        "height": height,
        "boot_s": boot_s,
        "rss_before": before,
        "rss_peak": peak,
        "rss_after_evict": after,
        "rss_after_close": closed,
        "growth": round(growth, 4),
        "cache_mb": report["cache"]["size_mb"],
        "cache_max_mb": report["cache"]["max_mb"],
        "gpu_available": report["gpu"]["available"],
        "gpu_code": report["gpu"].get("error_code"),
        "vram_used_mb": report["gpu"].get("vram_used_mb"),
        "ring_frames": report["video"]["frame_count"],
        "watchdog_alive": "di-watchdog" in names,
        "workers": report["workers"],
    }


def _switch_features(client: TestClient) -> None:
    for preset in ("light", "medium", "heavy"):
        opened = client.post("/models/switch", json={"name": "aquaclear", "preset": preset})
        opened.raise_for_status()
        closed = client.post("/models/switch", json={"name": "optical"})
        closed.raise_for_status()
    denied = client.post("/models/switch", json={"name": "hydrodetect"})
    if denied.status_code not in {404, 503}:
        denied.raise_for_status()
