"""Ganti fitur 50 kali dan pastikan VRAM kembali ke garis dasar.

Jalankan di PC inspeksi NVIDIA, dari folder v2:

    .venv/bin/python scripts/gpu_soak_test.py

Tanpa GPU skrip berhenti dengan kode 2. Itu bukan kelulusan.
"""

from __future__ import annotations

import sys
from pathlib import Path

from deepinsight_engine.core.config import load_settings
from deepinsight_engine.core.paths import default_config_dir
from deepinsight_engine.gpu.manager import ModelManager
from deepinsight_engine.gpu.probe import VramProbe

CYCLES = 50
ROOT = Path(__file__).resolve().parents[1]


def over_baseline(baseline_mb: float, used_mb: float, tolerance_mb: float) -> bool:
    return used_mb - baseline_mb > tolerance_mb


def main() -> int:
    settings = load_settings(default_config_dir())
    probe = VramProbe()
    baseline = probe.snapshot()
    if baseline is None:
        print("GPU tidak tersedia (D-01 / GPU-001). Uji VRAM wajib di PC NVIDIA.")
        return 2
    manager = _manager(settings, probe)
    names = _switchable(settings)
    print(f"garis dasar {baseline.used_mb:.1f} MB, fitur: {', '.join(names)}")
    try:
        for index in range(CYCLES):
            manager.switch(names[index % len(names)])
            manager.switch("optical")
            reading = probe.snapshot()
            if reading is None:
                print("pembacaan VRAM hilang di tengah uji")
                return 2
            if over_baseline(baseline.used_mb, reading.used_mb, _tolerance(settings)):
                print(f"gagal pada siklus {index + 1}: {reading.used_mb:.1f} MB")
                return 1
    finally:
        manager.close()
    print(f"lulus: {CYCLES} ganti fitur, VRAM kembali dalam toleransi")
    return 0


def _manager(settings: object, probe: VramProbe) -> ModelManager:
    from deepinsight_engine.core.config import Settings

    cfg = (
        settings
        if isinstance(settings, Settings)
        else load_settings(default_config_dir())
    )
    perf = cfg.thresholds.performance
    models = Path(cfg.app.models.dir)
    models_dir = models if models.is_absolute() else ROOT / models
    return ModelManager(
        cfg.models,
        models_dir,
        cfg.aquaclear.presets,
        cfg.aquaclear.default,
        probe,
        perf.unload_timeout_s,
        perf.load_timeout_s,
        perf.vram_baseline_tolerance_mb,
        lambda _code, _detail: None,
        hydro=cfg.hydrodetect,
        spatial=cfg.spatialsight,
    )


def _switchable(settings: object) -> list[str]:
    from deepinsight_engine.core.config import Settings

    cfg = (
        settings
        if isinstance(settings, Settings)
        else load_settings(default_config_dir())
    )
    names = ["aquaclear"]
    root = Path(cfg.app.models.dir)
    models_dir = root if root.is_absolute() else ROOT / root
    hydro = cfg.models.entries["hydrodetect"]
    spatial = cfg.models.entries["spatialsight"]
    if hydro.onnx and (models_dir / hydro.onnx).is_file():
        names.append("hydrodetect")
    if spatial.onnx and (models_dir / spatial.onnx).is_file():
        names.append("spatialsight")
    return names


def _tolerance(settings: object) -> float:
    from deepinsight_engine.core.config import Settings

    cfg = (
        settings
        if isinstance(settings, Settings)
        else load_settings(default_config_dir())
    )
    return cfg.thresholds.performance.vram_baseline_tolerance_mb


if __name__ == "__main__":
    sys.exit(main())
