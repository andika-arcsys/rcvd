from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from deepinsight_engine.core.config import load_settings
from deepinsight_engine.core.errors import EngineError


def test_repo_config_loads(config_dir: Path) -> None:
    settings = load_settings(config_dir)
    thr = settings.thresholds
    assert thr.span.critical_limit_m.inch_16 == 9.65
    assert thr.span.critical_limit_m.inch_8 == 5.32
    assert thr.rod_test.tolerance_pct == 3
    assert thr.freeze.max_delta_cm == 5
    assert thr.span.rope_tolerance_pct == 2
    assert thr.calibration.rel_uncertainty_basis == "2sigma"
    assert thr.calibration.camera_file_required_for_valid is True
    assert thr.span.resurvey_months == 6
    assert thr.measure.heron_rel_tol == 1e-9
    assert thr.measure.undistort_iterations == 20
    assert thr.calibration.min_baseline_px == 150
    assert thr.laser.ref_cm is None


def test_roles_matrix_is_complete(config_dir: Path) -> None:
    roles = load_settings(config_dir).roles
    assert len(roles.roles) == 7
    assert len(roles.menus) == 12
    assert roles.menus["pims_rbi"]["pilot_drone"] == "none"
    assert roles.menus["analisis_ai"]["teknisi_program"] == "full"
    assert all(row["ketua_tim"] != "none" for row in roles.menus.values())


def _copy_config(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst)
    return dst


def test_invalid_threshold_order_is_rejected(config_dir: Path, tmp_path: Path) -> None:
    cfg = _copy_config(config_dir, tmp_path / "cfg")
    path = cfg / "thresholds.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["calibration"]["valid_max_rel"] = 0.5
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(EngineError) as info:
        load_settings(cfg)
    assert info.value.spec.code == "SYS-001"
    assert "thresholds.yaml" in (info.value.detail or "")


def test_unknown_key_is_rejected(config_dir: Path, tmp_path: Path) -> None:
    cfg = _copy_config(config_dir, tmp_path / "cfg")
    path = cfg / "app.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["app"]["tidak_dikenal"] = 1
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(EngineError):
        load_settings(cfg)


def test_missing_file_is_reported(config_dir: Path, tmp_path: Path) -> None:
    cfg = _copy_config(config_dir, tmp_path / "cfg")
    (cfg / "roles.yaml").unlink()
    with pytest.raises(EngineError) as info:
        load_settings(cfg)
    assert info.value.spec.code == "SYS-001"
