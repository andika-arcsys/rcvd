"""Depth Anything 3: pilihan backend, inferensi palsu, dan pratinjau relatif."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from deepinsight_engine.core.config import load_settings
from deepinsight_engine.gpu.depth_anything3_runtime import DA3_WARNINGS, clamp_res, infer_depth
from deepinsight_engine.gpu.vision import RELATIVE_LABEL
from deepinsight_engine.gpu.worker import _da3_depth, _geometry, _infer_da3, _load_spatial
from deepinsight_engine.spatial.estimate import scene_from_message
from deepinsight_engine.spatial.source import spatial_choice

REPO = Path(__file__).resolve().parents[3] / "config"


def test_process_res_stays_on_the_console_sizes() -> None:
    assert clamp_res(504) == 504
    assert clamp_res(378) == 378
    assert clamp_res(672) == 672
    assert clamp_res(1024) == 504
    assert clamp_res(True) == 504
    assert clamp_res("504") == 504


def test_da3_choice_ignores_local_files(tmp_path: Path) -> None:
    weights = tmp_path / "spatialsight" / "depth_pro.pt"
    weights.parent.mkdir()
    weights.write_bytes(b"pt")
    chosen = spatial_choice(
        "depth_anything3",
        tmp_path,
        "spatialsight/model.onnx",
        "spatialsight/depth_pro.pt",
    )
    assert chosen == ("depth_anything3", None)


def test_settings_default_to_the_console_model() -> None:
    spatial = load_settings(REPO).spatialsight
    assert spatial.backend == "depth_anything3"
    assert spatial.model_id == "depth-anything/DA3METRIC-LARGE"
    assert spatial.process_res == 504


def test_infer_depth_uses_mini_npz_and_resizes(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = np.zeros((6, 8, 3), dtype=np.uint8)
    frame[0, 0] = (10, 20, 30)
    model = _FakeModel(np.ones((2, 2), dtype=np.float32))
    torch = _FakeTorch()
    monkeypatch.setattr(
        "deepinsight_engine.gpu.depth_anything3_runtime.importlib.import_module",
        _modules,
    )
    depth = infer_depth({"model": model, "torch": torch, "half": True}, frame, 672)
    assert depth.shape == (6, 8)
    assert model.process_res == 672
    assert model.export_format == "mini_npz"
    assert model.image[0][0, 0].tolist() == [30, 20, 10]
    assert torch.autocast_used is True


def test_da3_scene_keeps_the_reference_scale() -> None:
    depth = np.full((100, 100), 2.0, dtype=np.float32)
    scene = scene_from_message(
        depth,
        None,
        {
            "frame_id": "frm",
            "point_a": [50, 50],
            "point_b": [60, 50],
            "known_m": 0.4,
        },
        backend="Depth Anything 3",
        extra_warnings=DA3_WARNINGS,
    )
    assert scene["backend"] == "Depth Anything 3"
    assert scene["units"] == "METERS"
    assert scene["focal_px"] is None
    assert scene["distance_cm"] == pytest.approx(40.0)
    warnings = scene["warnings"]
    assert isinstance(warnings, list)
    assert any("belum dikalibrasi" in item for item in warnings)
    assert any("housing" in item for item in warnings)


def test_load_does_not_require_local_weights(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, object] = {}

    def fake(
        model_id: str, budget: float, pct: float, process_res: int
    ) -> tuple[dict[str, Any], str, bool]:
        seen["id"] = model_id
        seen["budget"] = budget
        seen["pct"] = pct
        seen["res"] = process_res
        return {"half": True}, "cuda note", True

    monkeypatch.setattr("deepinsight_engine.gpu.worker.load_model", fake)
    spatial = load_settings(REPO).spatialsight.model_dump()
    event = _load_spatial(
        {},
        tmp_path,
        {
            "spatial": spatial,
            "onnx": "spatialsight/model.onnx",
            "checkpoint": "spatialsight/depth_pro.pt",
            "process_res": 672,
            "vram_budget_mb": 6144,
            "gpu_max_pct": 90,
        },
    )
    assert event["event"] == "ready"
    assert event["device"] == "cuda note"
    assert seen == {
        "id": "depth-anything/DA3METRIC-LARGE",
        "budget": 6144.0,
        "pct": 90.0,
        "res": 672,
    }


def test_depth_pro_backend_still_names_missing_files(tmp_path: Path) -> None:
    spatial = load_settings(REPO).spatialsight.model_dump()
    spatial["backend"] = "depth_pro"
    event = _load_spatial(
        {},
        tmp_path,
        {
            "spatial": spatial,
            "onnx": "spatialsight/model.onnx",
            "checkpoint": "spatialsight/depth_pro.pt",
        },
    )
    assert event["code"] == "MDL-001"
    assert "depth_pro.pt" in str(event["detail"])


def test_live_preview_stays_relative(monkeypatch: pytest.MonkeyPatch) -> None:
    image = np.zeros((4, 4, 3), dtype=np.uint8)
    monkeypatch.setattr("deepinsight_engine.gpu.worker._read_raw", lambda _message: image.tobytes())

    def fake(_bundle: dict[str, Any], _image: Any, size: int) -> Any:
        assert size == 378
        grid = np.full((4, 4), 2.0, dtype=np.float32)
        grid[0, 0] = 8.0
        return grid

    monkeypatch.setattr("deepinsight_engine.gpu.worker.infer_depth", fake)
    event = _infer_da3(
        {
            "da3": {"half": False},
            "half": False,
            "process_res": 504,
            "spatial": {"preview_max_side": 64},
        },
        {"width": 4, "height": 4, "frame_id": "frm", "process_res": 378},
    )
    depth = event["depth"]
    assert isinstance(depth, dict)
    assert depth["label"] == RELATIVE_LABEL
    assert "m" not in str(depth["values"])


def test_half_failure_retries_in_fp32(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []

    def fake(bundle: dict[str, Any], _image: Any, _size: int) -> Any:
        calls.append(bool(bundle.get("half")))
        if bundle.get("half"):
            raise RuntimeError("half")
        return np.ones((2, 2), dtype=np.float32)

    monkeypatch.setattr("deepinsight_engine.gpu.worker.infer_depth", fake)
    state: dict[str, Any] = {"da3": {"half": True}, "half": True}
    depth = _da3_depth(state, np.zeros((2, 2, 3), dtype=np.uint8), 504)
    assert depth.shape == (2, 2)
    assert calls == [True, False]
    assert state["half"] is False


def test_frozen_geometry_names_depth_anything(monkeypatch: pytest.MonkeyPatch) -> None:
    image = np.zeros((8, 8, 3), dtype=np.uint8)
    monkeypatch.setattr("deepinsight_engine.gpu.worker._read_raw", lambda _message: image.tobytes())
    seen: dict[str, int] = {}

    def fake(_bundle: dict[str, Any], _image: Any, size: int) -> Any:
        seen["size"] = size
        return np.full((8, 8), 2.0, dtype=np.float32)

    monkeypatch.setattr("deepinsight_engine.gpu.worker.infer_depth", fake)
    event = _geometry(
        {
            "runtime": "depth_anything3",
            "da3": {"half": False},
            "half": False,
            "process_res": 504,
            "spatial": {"preview_max_side": 64},
        },
        {
            "width": 8,
            "height": 8,
            "frame_id": "frm",
            "point_a": [2, 4],
            "point_b": [6, 4],
            "known_m": 0.4,
            "process_res": 378,
        },
    )
    assert seen["size"] == 378
    assert event["backend"] == "Depth Anything 3"
    assert event["units"] == "METERS"
    assert event["distance_cm"] == pytest.approx(40.0)
    warnings = event["warnings"]
    assert isinstance(warnings, list)
    assert any("frozen frame" in item for item in warnings)


def test_onnx_geometry_stays_relative() -> None:
    event = _geometry({"runtime": "onnx"}, {})
    assert event["code"] == "MDL-002"
    assert "ONNX" in str(event["detail"])


class _FakeModel:
    def __init__(self, depth: Any) -> None:
        self._depth = depth
        self.process_res = 0
        self.export_format = ""
        self.image: list[Any] = []

    def inference(self, image: list[Any], process_res: int, export_format: str) -> Any:
        self.image = image
        self.process_res = process_res
        self.export_format = export_format
        return _Prediction(self._depth)


class _Prediction:
    def __init__(self, depth: Any) -> None:
        self.depth = [depth]


class _FakeTorch:
    float16 = "float16"

    def __init__(self) -> None:
        self.autocast_used = False

    def inference_mode(self) -> contextlib.AbstractContextManager[None]:
        return contextlib.nullcontext()

    def autocast(self, **_kwargs: object) -> contextlib.AbstractContextManager[None]:
        self.autocast_used = True
        return contextlib.nullcontext()


def _modules(name: str) -> Any:
    if name == "numpy":
        return np
    if name == "cv2":
        import cv2

        return cv2
    raise ImportError(name)
