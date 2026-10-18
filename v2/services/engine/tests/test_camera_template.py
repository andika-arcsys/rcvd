from __future__ import annotations

import shutil
from pathlib import Path

from deepinsight_engine.camera_calib import calibrate_folder
from deepinsight_engine.core.camera_file import camera_ids, rms_decision
from deepinsight_engine.core.config import load_settings
from deepinsight_engine.core.errors import EngineError


def test_rms_bands() -> None:
    assert rms_decision(0.5, 0.5, 1.0) == "accept"
    assert rms_decision(0.2, 0.5, 1.0) == "accept"
    assert rms_decision(0.8, 0.5, 1.0) == "warn"
    assert rms_decision(1.0, 0.5, 1.0) == "warn"
    assert rms_decision(1.2, 0.5, 1.0) == "reject"


def test_template_is_validated_and_not_listed(config_dir: Path) -> None:
    settings = load_settings(config_dir)
    assert settings.thresholds.camera.rms_good_px == 0.5
    assert settings.thresholds.camera.rms_max_px == 1.0
    assert settings.thresholds.laser.ref_cm == 10
    assert settings.procedure.sources == ["PR-06-019", "PR-06-111", "PR-06-117"]
    assert "_template" not in camera_ids(config_dir / "cameras")


def test_empty_pipelines_still_load(config_dir: Path, tmp_path: Path) -> None:
    shutil.copytree(config_dir, tmp_path / "config")
    target = tmp_path / "config" / "pipelines.yaml"
    target.write_text("schema_version: 1\npipelines: []\n", encoding="utf-8")
    assert load_settings(tmp_path / "config").pipelines.pipelines == []


def test_bad_camera_file_is_sys_001(config_dir: Path, tmp_path: Path) -> None:
    shutil.copytree(config_dir, tmp_path / "config")
    bad = tmp_path / "config" / "cameras" / "rusak.yaml"
    bad.write_text("schema_version: 1\nid: rusak\ncamera_matrix: [1]\n", encoding="utf-8")
    try:
        load_settings(tmp_path / "config")
    except EngineError as exc:
        assert exc.spec.code == "SYS-001"
    else:
        raise AssertionError("berkas kamera rusak harus SYS-001")


def test_calibrate_without_photos_does_not_write(config_dir: Path, tmp_path: Path) -> None:
    code, message = calibrate_folder(config_dir, tmp_path, "cam", 25, 9, 6)
    assert code == 2
    assert "Tidak ada foto" in message
    assert not (config_dir / "cameras" / "cam.yaml").exists()


def test_unreadable_photos_do_not_write(config_dir: Path, tmp_path: Path) -> None:
    photos = tmp_path / "foto"
    photos.mkdir()
    for name in ("a.png", "b.png", "c.png"):
        (photos / name).write_bytes(b"bukan-gambar")
    code, message = calibrate_folder(config_dir, photos, "cam", 25, 9, 6)
    assert code == 2
    assert "kurang dari 3" in message
    assert not (config_dir / "cameras" / "cam.yaml").exists()
