from __future__ import annotations

from pathlib import Path

from deepinsight_engine.core.config import load_settings
from deepinsight_engine.core.errors import EngineError
from deepinsight_engine.gpu.cache import CacheManager
from deepinsight_engine.gpu.probe import VramProbe, VramReading
from deepinsight_engine.gpu.watchdog import Watchdog

REPO_CONFIG = Path(__file__).resolve().parents[3] / "config"


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class _Probe(VramProbe):
    def __init__(self, used: float | None, util: float = 0.0, total: float = 100.0) -> None:
        self.used = used
        self.util = util
        self.total = total

    def snapshot(self) -> VramReading | None:
        if self.used is None:
            return None
        return VramReading(self.used, self.total, self.util)


def test_cache_evicts_oldest_and_rejects_evidence(tmp_path: Path) -> None:
    cache = CacheManager(tmp_path, max_mb=1)
    cache.put("a.bin", b"x" * 600_000)
    cache.put("b.bin", b"y" * 600_000)
    assert cache.get("a.bin") is None
    assert cache.get("b.bin") is not None
    try:
        cache.put("evidence/frame", b"no")
        raise AssertionError("bukti tidak boleh masuk cache")
    except EngineError as exc:
        assert exc.spec.code == "API-002"


def test_watchdog_fps_window_and_vram() -> None:
    perf = load_settings(REPO_CONFIG).thresholds.performance
    clock = _Clock()
    fps = {"value": 10.0}
    watchdog = Watchdog(perf, _Probe(None), lambda: fps["value"], clock)
    assert watchdog.tick() is None
    clock.now = perf.fps_window_s
    assert watchdog.tick() == "GPU-003"
    assert watchdog.detail == "fps"
    fps["value"] = perf.fps_min
    assert watchdog.tick() is None

    hot = Watchdog(perf, _Probe(perf.vram_max_pct + 1), lambda: None, clock)
    assert hot.tick() == "GPU-003"
    assert hot.detail == "vram"


def test_budget_is_six_gigabytes_and_ninety_percent() -> None:
    from deepinsight_engine.gpu.budget import process_memory_fraction

    perf = load_settings(REPO_CONFIG).thresholds.performance
    assert perf.vram_budget_mb == 6144
    assert perf.gpu_max_pct == 90
    assert perf.vram_max_pct == 75
    total = 8192 * 1024 * 1024
    used = 1024 * 1024 * 1024
    assert process_memory_fraction(total, used, 6144 * 1024 * 1024) == 5120 / 8192
    clock = _Clock()
    room = Watchdog(perf, _Probe(6000, total=8192), lambda: None, clock)
    assert room.tick() is None
    full = Watchdog(perf, _Probe(6145, total=8192), lambda: None, clock)
    assert full.tick() == "GPU-003"
    assert full.detail == "vram"
    busy = Watchdog(perf, _Probe(1000, util=91, total=8192), lambda: None, clock)
    assert busy.tick() is None
    clock.now = perf.gpu_window_s
    assert busy.tick() == "GPU-003"
    assert busy.detail == "gpu"
