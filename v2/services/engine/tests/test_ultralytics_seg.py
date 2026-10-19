"""Bobot .pt diutamakan. Konversi hasil Ultralytics tidak membutuhkan GPU."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from deepinsight_engine.core.config import load_settings
from deepinsight_engine.core.errors import EngineError
from deepinsight_engine.gpu.budget import limit_process_memory, try_limit_process_memory
from deepinsight_engine.gpu.manager import ModelManager
from deepinsight_engine.gpu.probe import SequenceProbe
from deepinsight_engine.gpu.process import WorkerHandle
from deepinsight_engine.gpu.ultralytics_seg import (
    cpu_fallback_note,
    hydro_source,
    predict_candidates,
)

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
        assert _kwargs["retina_masks"] is True
        assert _kwargs["verbose"] is False
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


def test_live_confidence_and_quality_reach_ultralytics() -> None:
    settings = load_settings(REPO)
    seen: dict[str, object] = {}

    class _Recording(_Model):
        def predict(self, image: np.ndarray, **kwargs: object) -> list[_Result]:
            seen.update(kwargs)
            return super().predict(image, **kwargs)

    image = np.zeros((12, 16, 3), dtype=np.uint8)
    found = predict_candidates(
        _Recording(),
        image,
        list(settings.hydrodetect.filter_names),
        settings.hydrodetect,
        "cpu",
        confidence=0.8,
        imgsz=1280,
    )
    assert seen["conf"] == 0.8
    assert seen["imgsz"] == 1280
    assert seen["device"] == "cpu"
    assert seen["quantize"] is None
    assert "half" not in seen
    assert len(found) == 1
    assert found[0]["class_name"] == "Leakage"


def test_cuda_device_keeps_the_original_frame_and_asks_for_fp16() -> None:
    settings = load_settings(REPO)
    seen: dict[str, object] = {}

    class _Recording(_Model):
        def predict(self, image: np.ndarray, **kwargs: object) -> list[_Result]:
            seen["shape"] = image.shape
            seen.update(kwargs)
            return super().predict(image, **kwargs)

    image = np.zeros((12, 16, 3), dtype=np.uint8)
    predict_candidates(
        _Recording(),
        image,
        list(settings.hydrodetect.filter_names),
        settings.hydrodetect,
        "0",
        confidence=0.7,
        imgsz=1280,
    )
    assert seen["shape"] == (12, 16, 3)
    assert seen["device"] == "0"
    assert seen["quantize"] == 16
    assert "half" not in seen
    assert seen["conf"] == 0.7
    assert seen["imgsz"] == 1280
    assert seen["retina_masks"] is True


class _Cuda:
    def __init__(self) -> None:
        self.fraction = 0.0

    def mem_get_info(self) -> tuple[int, int]:
        total = 8192 * 1024 * 1024
        used = 1024 * 1024 * 1024
        return total - used, total

    def set_per_process_memory_fraction(self, fraction: float) -> None:
        self.fraction = fraction


class _Torch:
    def __init__(self) -> None:
        self.cuda = _Cuda()


def test_six_gigabyte_cap_on_an_eight_gigabyte_card() -> None:
    torch = _Torch()
    note = limit_process_memory(torch, 6144)
    assert torch.cuda.fraction == 5120 / 8192
    assert note == "cap=5120/6144MB"


def test_cpu_note_stays_a_cpu_sentence() -> None:
    assert cpu_fallback_note().startswith("cpu")


class _RejectingCuda(_Cuda):
    def set_per_process_memory_fraction(self, fraction: float) -> None:
        raise RuntimeError("allocator sudah hidup")


def test_allocator_refusal_does_not_block_the_model() -> None:
    note = try_limit_process_memory(_TorchReplace(), 6144)
    assert note.startswith("cap=lewati")
    assert "allocator sudah hidup" in note


class _TorchReplace(_Torch):
    def __init__(self) -> None:
        self.cuda = _RejectingCuda()


def test_library_banner_on_stdout_does_not_drop_the_ready_event() -> None:
    handle = WorkerHandle(1)
    handle._queue.put("Ultralytics 8.4.105  Python-3.12 torch-2.13.0+cu132\n")
    handle._queue.put('{"event": "ready", "fp16": true, "device": "cuda half"}\n')
    event = handle.read_event()
    assert event["event"] == "ready"
    assert event["fp16"] is True


def test_old_ultralytics_without_quantize_uses_half() -> None:
    settings = load_settings(REPO)
    seen: dict[str, object] = {}

    class _Legacy(_Model):
        def predict(self, image: np.ndarray, **kwargs: object) -> list[_Result]:
            if "quantize" in kwargs:
                raise TypeError("unexpected keyword argument 'quantize'")
            seen.update(kwargs)
            return super().predict(image, **kwargs)

    image = np.zeros((12, 16, 3), dtype=np.uint8)
    predict_candidates(
        _Legacy(),
        image,
        list(settings.hydrodetect.filter_names),
        settings.hydrodetect,
        "0",
    )
    assert seen["half"] is True
    assert "quantize" not in seen


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
