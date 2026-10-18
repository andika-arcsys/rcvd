from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

from deepinsight_engine.gpu.probe import VramProbe

ROOT = Path(__file__).resolve().parents[3]
PYTHON = Path(sys.executable)


def _soak():
    path = ROOT / "scripts" / "gpu_soak_test.py"
    spec = importlib.util.spec_from_file_location("gpu_soak_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_vram_limit_is_above_baseline() -> None:
    over = _soak().over_baseline
    assert over(100, 130, 20) is True
    assert over(100, 110, 20) is False


def test_soak_refuses_without_gpu() -> None:
    if VramProbe().snapshot() is not None:
        return
    completed = subprocess.run(
        [str(PYTHON), str(ROOT / "scripts" / "gpu_soak_test.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
    assert "NVIDIA" in completed.stdout


def test_eval_refuses_without_labeled_samples() -> None:
    completed = subprocess.run(
        [str(PYTHON), str(ROOT / "scripts" / "eval_hydrodetect.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
    assert "D-17" in completed.stdout
