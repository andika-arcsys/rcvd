"""Bobot .pt diutamakan. Konversi hasil Ultralytics tidak membutuhkan GPU."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from deepinsight_engine.core.config import load_settings
from deepinsight_engine.core.errors import EngineError
from deepinsight_engine.gpu.manager import ModelManager
from deepinsight_engine.gpu.probe import SequenceProbe
from deepinsight_engine.gpu.ultralytics_seg import hydro_source, predict_candidates

REPO = Path(__file__).resolve().parents[3] / "config"


class _Tensor:
    def __init__(self, values: list[object]) -> None:
        self._values = np.asarray(values)

    def detach(self) -> _Tensor:
        return self

    def cpu(self) -> _Tensor:
        return self

    def numpy(self) -> np.ndarray:
        return self._values


class _Boxes:
    cls = _Tensor([0, 1])
    conf = _Tensor([0.92, 0.1])
    xyxy = _Tensor([[2, 2, 8, 8], [0, 0, 2, 2]])


class _Masks:
    xy = [np.array([[2.2, 2.4], [8.2, 2.1], [7.6, 8.3], [2.1, 7.8]])]


class _Result:
    boxes = _Boxes()
    masks = _Masks()


class _Model:
    def predict(self, image: np.ndarray, **_kwargs: object) -> list[_Result]:
        assert image.shape == (12, 16, 3)
        assert _kwargs["device"] == "cpu"
        assert _kwargs["retina_masks"] is True
        return [_Result()]


def test_pt_is_preferred_over_onnx(tmp_path: Path) -> None:
    weights = tmp_path / "model.pt"
    onnx = tmp_path / "model.onnx"
    weights.write_bytes(b"pt")
    onnx.write_bytes(b"onnx")
    assert hydro_source(tmp_path, "model.pt", "model.onnx") == ("ultralytics", weights)
    weights.unlink()
    assert hydro_source(tmp_path, "model.pt", "model.onnx") == ("onnx", onnx)
    onnx.unlink()
    assert hydro_source(tmp_path, "model.pt", "model.onnx") is None


def test_ultralytics_result_keeps_trained_class_on_raw_frame() -> None:
    settings = load_settings(REPO)
    image = np.zeros((12, 16, 3), dtype=np.uint8)
    found = predict_candidates(
        _Model(),
        image,
        list(settings.hydrodetect.filter_names),
        settings.hydrodetect,
        "cpu",
    )
    assert len(found) == 1
    assert found[0]["class_name"] == "Leakage"
    assert found[0]["score"] == 0.92
    assert found[0]["polygon"][0] == [2, 2]
    assert found[0]["bbox"] == [2, 2, 6, 6]
    assert found[0]["rle"]


def test_present_pt_asks_for_ultralytics(tmp_path: Path) -> None:
    settings = load_settings(REPO)
    target = tmp_path / "hydrodetect" / "exp5" / "model.pt"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"bukan bobot")
    perf = settings.thresholds.performance
    manager = ModelManager(
        settings.models,
        tmp_path,
        settings.aquaclear.presets,
        settings.aquaclear.default,
        SequenceProbe([100.0]),
        perf.unload_timeout_s,
        perf.load_timeout_s,
        perf.vram_baseline_tolerance_mb,
        lambda _code, _detail: None,
    )
    with pytest.raises(EngineError) as info:
        manager.switch("hydrodetect")
    assert info.value.spec.code == "MDL-002"
    assert "ultralytics" in (info.value.detail or "")
    assert manager.state == "optical"
