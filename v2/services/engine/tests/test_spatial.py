"""Geometri SpatialSight dan pilihan berkas, tanpa GPU."""

from __future__ import annotations

import threading
from pathlib import Path

import numpy as np
import pytest

from deepinsight_engine.core.errors import EngineError
from deepinsight_engine.gpu.vision import RELATIVE_LABEL
from deepinsight_engine.spatial.band import scored_depth
from deepinsight_engine.spatial.estimate import estimate_scene
from deepinsight_engine.spatial.geometry import (
    CameraIntrinsics,
    ScaleCalibration,
    calibration_from_reference,
    clockwise_screen_deg,
    default_intrinsics,
    measure_distance,
)
from deepinsight_engine.spatial.preview import relative_preview, turbo_bgr
from deepinsight_engine.spatial.source import missing_spatial_detail, spatial_source
from tests.test_models import _manager


def test_flat_plane_matches_reference_scale() -> None:
    depth = np.full((100, 100), 2.0, dtype=np.float32)
    intrinsics = default_intrinsics(100, 100, 100.0)
    raw = measure_distance((50, 50), (60, 50), depth, intrinsics, ScaleCalibration())
    assert raw.distance_m == pytest.approx(0.2)
    assert raw.validity == "UNCALIBRATED"
    scale = calibration_from_reference(
        (50, 50),
        (60, 50),
        0.4,
        depth,
        intrinsics,
        source="REFERENCE_SCALED",
        frame_id="frm",
    )
    assert scale.scale == pytest.approx(2.0)
    scaled = measure_distance((50, 50), (60, 50), depth, intrinsics, scale, frame_id="frm")
    assert scaled.distance_m == pytest.approx(0.4)
    assert scaled.validity == "ESTIMATE_ONLY_SAME_FRAME"
    water = CameraIntrinsics(100, 100, 50, 50, calibrated_underwater=True)
    valid = measure_distance((50, 50), (60, 50), depth, water, scale, frame_id="frm")
    assert valid.validity == "VALID_SAME_FRAME"
    crossed = measure_distance((50, 50), (60, 50), depth, intrinsics, scale, frame_id="lain")
    assert crossed.validity == "INVALID_CROSS_FRAME"


def test_line_angle_is_clockwise_from_the_screen_horizontal() -> None:
    assert clockwise_screen_deg((0.0, 0.0), (10.0, 0.0)) == pytest.approx(0.0)
    assert clockwise_screen_deg((0.0, 0.0), (10.0, 10.0)) == pytest.approx(45.0)
    assert clockwise_screen_deg((0.0, 0.0), (0.0, 10.0)) == pytest.approx(90.0)
    assert clockwise_screen_deg((0.0, 0.0), (-10.0, 0.0)) == pytest.approx(180.0)
    assert clockwise_screen_deg((0.0, 0.0), (0.0, -10.0)) == pytest.approx(270.0)
    depth = np.full((40, 40), 2.0, dtype=np.float32)
    scene = estimate_scene(
        depth,
        100.0,
        "frm",
        ((5.0, 20.0), (15.0, 20.0)),
        0.4,
        [((10.0, 8.0), (10.0, 28.0))],
        [],
        [],
    )
    lengths = scene["lengths"]
    assert isinstance(lengths, list)
    assert lengths[0]["angle_deg"] == pytest.approx(90.0)
    assert scene["cal_angle_deg"] == pytest.approx(0.0)


def test_scene_keeps_mesh_off_the_two_dimensional_status() -> None:
    depth = np.full((40, 40), 2.0, dtype=np.float32)
    scene = estimate_scene(
        depth,
        100.0,
        "frm",
        ((10.0, 10.0), (20.0, 10.0)),
        0.4,
        [((10.0, 10.0), (30.0, 10.0))],
        [[(8.0, 8.0), (24.0, 8.0), (24.0, 24.0), (8.0, 24.0)]],
        [[(10.0, 12.0), (20.0, 12.0), (20.0, 22.0)]],
    )
    assert scene["validity"] == "ESTIMATE_ONLY_SAME_FRAME"
    assert scene["underwater_intrinsics"] is False
    assert scene["backend"] == "Apple Depth Pro"
    assert scene["distance_cm"] == pytest.approx(40.0)
    lengths = scene["lengths"]
    assert isinstance(lengths, list)
    assert lengths[0]["distance_cm"] == pytest.approx(80.0)
    assert lengths[0]["validity"] == "ESTIMATE_ONLY_SAME_FRAME"
    assert lengths[0]["angle_deg"] == pytest.approx(0.0)
    assert scene["cal_angle_deg"] == pytest.approx(0.0)
    areas = scene["areas"]
    assert isinstance(areas, list)
    assert float(areas[0]["area_cm2"]) > 0
    paths = scene["paths"]
    assert isinstance(paths, list)
    assert float(paths[0]["path_cm"]) > 0
    warnings = scene["warnings"]
    assert isinstance(warnings, list)
    assert any("housing" in item for item in warnings)


def test_farther_span_uses_midpoint_depth_not_the_rims() -> None:
    depth = np.full((40, 80), 2.0, dtype=np.float32)
    depth[17:24, 17:24] = 4.0
    depth[20, 10] = 8.0
    depth[20, 30] = 0.4
    scene = estimate_scene(
        depth,
        100.0,
        "frm",
        ((10.0, 10.0), (20.0, 10.0)),
        0.4,
        [((10.0, 20.0), (30.0, 20.0))],
        [],
        [],
    )
    lengths = scene["lengths"]
    assert isinstance(lengths, list)
    assert scene["distance_cm"] == pytest.approx(40.0)
    assert lengths[0]["distance_cm"] == pytest.approx(160.0 * scored_depth(4.0, 2.0) / 4.0)
    assert lengths[0]["depth"] == pytest.approx(4.0)


def test_nearer_depth_is_brighter_in_the_relative_preview() -> None:
    depth = np.ones((4, 4), dtype=np.float32)
    depth[0, 0] = 10.0
    preview = relative_preview(depth, 64)
    assert preview["label"] == RELATIVE_LABEL
    values = preview["values"]
    assert isinstance(values, list)
    assert float(values[0]) < float(values[1])


def test_turbo_paints_near_warm_and_far_cool() -> None:
    depth = np.full((40, 40), 5.0, dtype=np.float32)
    depth[:8, :] = 1.0
    depth[-8:, :] = 12.0
    colored = turbo_bgr(depth)
    near = colored[2, 20]
    far = colored[-3, 20]
    assert int(near[2]) > int(far[2])
    assert int(far[0]) > int(near[0])
    preview = relative_preview(depth, 64)
    jpeg = preview.get("jpeg_b64")
    assert isinstance(jpeg, str) and jpeg.startswith("/9j/")


def test_checkpoint_is_preferred_over_onnx(tmp_path: Path) -> None:
    checkpoint = tmp_path / "spatialsight" / "depth_pro.pt"
    onnx = tmp_path / "spatialsight" / "model.onnx"
    checkpoint.parent.mkdir()
    checkpoint.write_bytes(b"pt")
    onnx.write_bytes(b"onnx")
    chosen = spatial_source(tmp_path, "spatialsight/model.onnx", "spatialsight/depth_pro.pt")
    assert chosen is not None
    assert chosen[0] == "depth_pro"
    onnx_only = spatial_source(tmp_path, "spatialsight/model.onnx", "spatialsight/hilang.pt")
    assert onnx_only is not None
    assert onnx_only[0] == "onnx"
    assert spatial_source(tmp_path, "tidak-ada.onnx", "tidak-ada.pt") is None
    detail = missing_spatial_detail("spatialsight/model.onnx", "spatialsight/depth_pro.pt")
    assert "depth_pro.pt" in detail
    assert "model.onnx" in detail


def test_missing_spatial_names_both_files(tmp_path: Path) -> None:
    manager = _manager(tmp_path, [100.0])
    with pytest.raises(EngineError) as info:
        manager.switch("spatialsight")
    assert info.value.spec.code in {"MDL-002", "MDL-003"}
    detail = info.value.detail or ""
    assert "depth_pro.pt" not in detail
    assert manager.state == "optical"


def test_estimate_without_evidence_is_rejected(secured_client: object) -> None:
    from fastapi.testclient import TestClient

    assert isinstance(secured_client, TestClient)
    response = secured_client.post(
        "/spatial/estimate",
        headers={"X-DeepInsight-Token": "rahasia-uji"},
        json={
            "frame_id": "frm-hilang",
            "ref_cm": 10,
            "calibration": {"a": {"x": 1, "y": 1}, "b": {"x": 20, "y": 1}},
        },
    )
    assert response.status_code == 410
    assert response.json()["code"] == "VID-002"


class _CycleModels:
    def __init__(self) -> None:
        self.active: str | None = None
        self.state = "optical"
        self.switches: list[str] = []
        self.geometry_calls = 0
        self.fail = False

    def switch(self, name: str, preset: str | None = None) -> None:
        del preset
        self.switches.append(name)
        if name == "optical":
            self.active = None
            self.state = "optical"
            return
        self.active = name
        self.state = "ready"

    def geometry(
        self, raw: bytes, width: int, height: int, frame_id: str, spec: dict[str, object]
    ) -> dict[str, object]:
        del raw, width, height, frame_id
        self.geometry_calls += 1
        if self.fail:
            raise EngineError("MDL-002", "gagal")
        lengths = spec.get("lengths")
        return {"event": "result", "kind": "spatial-geometry", "lengths": lengths}


class _CycleInfer:
    def __init__(self) -> None:
        self.cancels = 0

    def cancel(self) -> None:
        self.cancels += 1


def _runtime_for_cycle(tmp_path: Path, models: _CycleModels) -> object:
    from deepinsight_engine.runtime import Runtime

    runtime = Runtime.__new__(Runtime)
    runtime._evidence = tmp_path
    runtime._assist_lock = threading.Lock()
    runtime._live_infer = _CycleInfer()
    runtime.models = models
    (tmp_path / "frm-uji.png").write_bytes(b"png")
    return runtime


def test_estimate_spatial_runs_once_then_unloads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "deepinsight_engine.video.decode.decode_png",
        lambda _data: (8, 8, b"\x00" * (8 * 8 * 3)),
    )
    models = _CycleModels()
    runtime = _runtime_for_cycle(tmp_path, models)
    spec = {"lengths": [{}, {}, {}], "known_m": 0.4}
    result = runtime.estimate_spatial("frm-uji", spec)  # type: ignore[attr-defined]
    assert result["kind"] == "spatial-geometry"
    assert models.geometry_calls == 1
    assert models.switches == ["spatialsight", "optical"]
    assert models.active is None
    assert models.state == "optical"
    assert runtime._live_infer.cancels >= 2  # type: ignore[attr-defined]


def test_estimate_spatial_unloads_when_geometry_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "deepinsight_engine.video.decode.decode_png",
        lambda _data: (8, 8, b"\x00" * (8 * 8 * 3)),
    )
    models = _CycleModels()
    models.fail = True
    runtime = _runtime_for_cycle(tmp_path, models)
    with pytest.raises(EngineError) as info:
        runtime.estimate_spatial("frm-uji", {"lengths": [{}]})  # type: ignore[attr-defined]
    assert info.value.spec.code == "MDL-002"
    assert models.geometry_calls == 1
    assert models.switches == ["spatialsight", "optical"]
    assert models.active is None


def test_turbo_jpeg_failure_keeps_the_numeric_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    import cv2

    def boom(_image: object, _colormap: int) -> None:
        raise cv2.error("colormap gagal")

    monkeypatch.setattr(cv2, "applyColorMap", boom)
    preview = relative_preview(np.full((32, 32), 2.0, dtype=np.float32), 64)
    values = preview["values"]
    assert isinstance(values, list)
    assert values
    assert "jpeg_b64" not in preview
