from __future__ import annotations

import os
from pathlib import Path

import pytest

from deepinsight_engine.core.config import load_settings
from deepinsight_engine.core.errors import EngineError
from deepinsight_engine.gpu.aquaclear import apply_preset
from deepinsight_engine.gpu.manager import ModelManager
from deepinsight_engine.gpu.probe import SequenceProbe
from deepinsight_engine.video.synthetic import gradient_bgr

REPO_CONFIG = Path(__file__).resolve().parents[3] / "config"


def _manager(tmp_path: Path, used: list[float | None], **kwargs: object) -> ModelManager:
    settings = load_settings(REPO_CONFIG)
    perf = settings.thresholds.performance
    return ModelManager(
        settings.models,
        tmp_path,
        settings.aquaclear.presets,
        settings.aquaclear.default,
        SequenceProbe(used),
        float(kwargs.get("unload", perf.unload_timeout_s)),  # type: ignore[arg-type]
        float(kwargs.get("load", perf.load_timeout_s)),  # type: ignore[arg-type]
        perf.vram_baseline_tolerance_mb,
        kwargs.get("on_error", lambda _code, _detail: None),  # type: ignore[arg-type]
        kwargs.get("env"),  # type: ignore[arg-type]
    )


def test_aquaclear_changes_pixels() -> None:
    settings = load_settings(REPO_CONFIG)
    raw = gradient_bgr(32, 24, 1)
    out = apply_preset(raw, 32, 24, settings.aquaclear.presets[settings.aquaclear.default])
    assert out != raw
    assert len(out) == len(raw)


def test_missing_weight_returns_to_optical(tmp_path: Path) -> None:
    manager = _manager(tmp_path, [100.0])
    with pytest.raises(EngineError) as info:
        manager.switch("hydrodetect")
    assert info.value.spec.code == "MDL-001"
    assert manager.state == "optical"
    assert manager.workers == 0


def test_switch_kills_worker_when_vram_returns(tmp_path: Path) -> None:
    manager = _manager(tmp_path, [100.0, 100.0])
    manager.switch("aquaclear")
    pid = manager.worker_pid
    assert pid is not None
    manager.switch("optical")
    assert manager.state == "optical"
    assert manager.killed_for_vram is False
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_worker_is_killed_when_vram_does_not_return(tmp_path: Path) -> None:
    seen: list[str] = []
    manager = _manager(
        tmp_path,
        [100.0, 1000.0],
        unload=0.3,
        on_error=lambda code, _detail: seen.append(code),
        env={"DEEPINSIGHT_WORKER_HOLD": "1"},
    )
    manager.switch("aquaclear")
    pid = manager.worker_pid
    assert pid is not None and manager.state == "ready"
    manager.switch("optical")
    assert manager.killed_for_vram
    assert "GPU-002" in seen
    assert manager.state == "optical"
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
