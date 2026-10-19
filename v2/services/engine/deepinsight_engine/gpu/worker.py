"""Proses pekerja: satu model. AquaClear dan HydroDetect di CUDA bila ada."""

from __future__ import annotations

import importlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from ..core.config import AquaPreset
from ..core.errors import EngineError
from ..spatial.estimate import scene_from_message
from ..spatial.preview import relative_preview
from ..spatial.source import missing_spatial_detail, spatial_source
from .aquaclear import enhance_live, open_enhancer
from .depth_map import relative_from_output
from .depth_pro_runtime import infer_meters, load_depth_pro
from .ultralytics_seg import (
    IMGSZ,
    QUALITY_SIZES,
    cpu_fallback_note,
    hydro_source,
    load_yolo,
    missing_hydro_detail,
    names_of,
    predict_candidates,
    prepare_detector,
    torch_device,
)
from .vision import RELATIVE_LABEL, depth_event, hydro_event
from .yolo_seg import decode_yolo_seg


def main() -> None:
    from .tensorflow_mem import enable_memory_growth

    enable_memory_growth()
    state: dict[str, Any] = {"kind": None, "preset": None, "session": None}
    for line in sys.stdin:
        message = json.loads(line)
        command = str(message.get("cmd"))
        if command == "quit":
            break
        if command == "load":
            _emit(_load(state, message))
        elif command == "infer":
            _emit(_infer(state, message))
        elif command == "geometry":
            _emit(_geometry(state, message))
        elif command == "unload":
            _hold_if_requested()
            state["session"] = None
            state["yolo"] = None
            state["classes"] = None
            state["hydro"] = None
            state["runtime"] = None
            state["depth_pro"] = None
            state["tensor"] = None
            state["enhancer"] = None
            _emit({"event": "unloaded"})


def _load(state: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
    kind = str(message["kind"])
    root = Path(str(message["models_dir"]))
    if kind == "hydrodetect":
        loaded = _load_hydro(state, root, message)
        if loaded is not None:
            return loaded
    if kind == "spatialsight":
        return _load_spatial(state, root, message)
    missing = _missing_file(kind, root, message)
    if missing:
        return {"event": "error", "code": "MDL-001", "detail": missing}
    if kind == "aquaclear":
        state["preset"] = AquaPreset.model_validate(message["preset"])
        state["max_side"] = int(message.get("display_max_side") or 0)
        state["vram_budget_mb"] = float(message.get("vram_budget_mb") or 0)
        state["gpu_max_pct"] = float(message.get("gpu_max_pct") or 90)
        state["enhancer"], note = open_enhancer(
            state["preset"],
            state["max_side"],
            state["vram_budget_mb"],
            state["gpu_max_pct"],
        )
        state["meta"] = {"fp16": bool(getattr(state["enhancer"], "uses_cuda", False))}
        state["device_note"] = note
        preset_name = state["preset"].pipeline
        sys.stderr.write(f"AquaClear enhancer: {note} preset={preset_name}\n")
        sys.stderr.flush()
    else:
        opened = _open_session(root / str(message["onnx"]))
        if isinstance(opened, dict):
            return opened
        state["session"] = opened
        state["meta"] = _input_meta(opened)
        try:
            _remember_side(state, kind, root, message)
        except EngineError as exc:
            state["session"] = None
            return {"event": "error", "code": exc.spec.code, "detail": exc.detail or ""}
    state["kind"] = kind
    return {
        "event": "ready",
        "fp16": bool(state.get("meta", {}).get("fp16")),
        "device": state.get("device_note"),
    }


def _load_hydro(
    state: dict[str, Any], root: Path, message: dict[str, Any]
) -> dict[str, Any] | None:
    weights = None if message.get("weights") is None else str(message.get("weights"))
    onnx = None if message.get("onnx") is None else str(message.get("onnx"))
    picked = hydro_source(root, weights, onnx)
    if picked is None:
        return {"event": "error", "code": "MDL-001", "detail": missing_hydro_detail(weights, onnx)}
    runtime, path = picked
    if runtime != "ultralytics":
        return None
    try:
        model = load_yolo(path)
        classes = names_of(model)
        hydro = _hydro_config(message)
    except EngineError as exc:
        return {"event": "error", "code": exc.spec.code, "detail": exc.detail or ""}
    device = torch_device()
    size = _load_imgsz(message)
    try:
        note = _place_hydro(model, device, message, size)
    except EngineError as exc:
        return {"event": "error", "code": exc.spec.code, "detail": exc.detail or ""}
    state["yolo"] = model
    state["classes"] = classes
    state["hydro"] = hydro
    state["device"] = device
    state["imgsz"] = size
    state["runtime"] = "ultralytics"
    state["kind"] = "hydrodetect"
    state["device_note"] = note
    sys.stderr.write(f"HydroDetect: {note} imgsz={size}\n")
    sys.stderr.flush()
    return {"event": "ready", "fp16": device != "cpu", "device": note}


def _load_spatial(state: dict[str, Any], root: Path, message: dict[str, Any]) -> dict[str, Any]:
    onnx = _opt_str(message.get("onnx"))
    checkpoint = _opt_str(message.get("checkpoint"))
    picked = spatial_source(root, onnx, checkpoint)
    if picked is None:
        detail = missing_spatial_detail(onnx, checkpoint)
        return {"event": "error", "code": "MDL-001", "detail": detail}
    runtime, path = picked
    try:
        _remember_side(state, "spatialsight", root, message)
    except EngineError as exc:
        return {"event": "error", "code": exc.spec.code, "detail": exc.detail or ""}
    if runtime == "depth_pro":
        return _ready_depth_pro(state, path)
    opened = _open_session(path)
    if isinstance(opened, dict):
        return opened
    state["session"] = opened
    state["meta"] = _input_meta(opened)
    state["runtime"] = "onnx"
    state["kind"] = "spatialsight"
    return {"event": "ready", "fp16": bool(state["meta"].get("fp16"))}


def _ready_depth_pro(state: dict[str, Any], path: Path) -> dict[str, Any]:
    try:
        state["depth_pro"] = load_depth_pro(path)
    except EngineError as exc:
        return {"event": "error", "code": exc.spec.code, "detail": exc.detail or ""}
    state["runtime"] = "depth_pro"
    state["kind"] = "spatialsight"
    return {"event": "ready", "fp16": True}


def _opt_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _hydro_config(message: dict[str, Any]) -> Any:
    from ..core.config import HydrodetectConfig

    return HydrodetectConfig.model_validate(message.get("hydro"))


def _missing_file(kind: str, root: Path, message: dict[str, Any]) -> str | None:
    if kind == "aquaclear":
        return None
    for field in ("onnx", "classes"):
        relative = message.get(field)
        if relative and not (root / str(relative)).is_file():
            return str(relative)
    return None


def _remember_side(state: dict[str, Any], kind: str, root: Path, message: dict[str, Any]) -> None:
    if kind == "hydrodetect":
        from ..core.config import HydrodetectConfig

        state["classes"] = _read_classes(root / str(message["classes"]))
        state["hydro"] = HydrodetectConfig.model_validate(message.get("hydro"))
        return
    side = message.get("spatial") or {}
    if str(side.get("relative_label") or "") != RELATIVE_LABEL:
        raise EngineError("MDL-002", "label SpatialSight")
    state["spatial"] = side


def _read_classes(path: Path) -> list[str]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list) or not all(isinstance(item, str) for item in loaded):
        raise EngineError("MDL-002", "classes.json harus berupa daftar nama")
    return [str(item) for item in loaded]


def _open_session(path: Path) -> Any:
    try:
        ort = importlib.import_module("onnxruntime")
    except ImportError:
        return {"event": "error", "code": "MDL-002", "detail": "onnxruntime belum terpasang"}
    if "CUDAExecutionProvider" not in ort.get_available_providers():
        return {"event": "error", "code": "MDL-003", "detail": "CUDAExecutionProvider"}
    try:
        options = ort.SessionOptions()
        return ort.InferenceSession(
            str(path),
            sess_options=options,
            providers=["CUDAExecutionProvider"],
        )
    except Exception as exc:  # noqa: BLE001 - ORT melempar error khusus yang tidak diimpor
        return {"event": "error", "code": "MDL-002", "detail": str(exc)}


def _input_meta(session: Any) -> dict[str, Any]:
    entry = session.get_inputs()[0]
    shape = list(entry.shape)
    height = shape[2] if len(shape) > 2 and isinstance(shape[2], int) else None
    width = shape[3] if len(shape) > 3 and isinstance(shape[3], int) else None
    fp16 = "float16" in str(entry.type)
    return {"name": entry.name, "height": height, "width": width, "fp16": fp16}


def _infer(state: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
    if state["kind"] == "aquaclear":
        out_w, out_h = _write_aquaclear(state, message)
        return {
            "event": "result",
            "frame_id": message["frame_id"],
            "enhanced": True,
            "kind": "aquaclear",
            "out_width": out_w,
            "out_height": out_h,
        }
    if state.get("runtime") == "ultralytics":
        return _infer_ultra(state, message)
    if state.get("runtime") == "depth_pro":
        return _infer_depth(state, message)
    if state["session"] is None:
        return {"event": "error", "code": "MDL-002", "detail": "sesi model kosong"}
    try:
        return _infer_onnx(state, message)
    except EngineError as exc:
        return {"event": "error", "code": exc.spec.code, "detail": exc.detail or ""}


def _infer_ultra(state: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
    np = importlib.import_module("numpy")
    width, height = int(message["width"]), int(message["height"])
    image = np.frombuffer(_read_raw(message), dtype=np.uint8).reshape(height, width, 3)
    try:
        found = predict_candidates(
            state["yolo"],
            image,
            state["classes"],
            state["hydro"],
            str(state["device"]),
            confidence=_tune_confidence(message),
            imgsz=_tune_imgsz(message),
        )
    except EngineError as exc:
        return {"event": "error", "code": exc.spec.code, "detail": exc.detail or ""}
    except Exception as exc:  # noqa: BLE001 - inferensi model tidak boleh mematikan pekerja
        return {"event": "error", "code": "MDL-002", "detail": str(exc)}
    return hydro_event(str(message["frame_id"]), found)


def _infer_onnx(state: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
    np = importlib.import_module("numpy")
    width, height = int(message["width"]), int(message["height"])
    tensor = _tensor(np, _read_raw(message), width, height, state["meta"])
    session = state["session"]
    outputs = session.run(None, {str(state["meta"]["name"]): tensor})
    del tensor
    frame_id = str(message["frame_id"])
    if state["kind"] == "hydrodetect":
        found = decode_yolo_seg(outputs, state["classes"], width, height, state["hydro"])
        del outputs
        return hydro_event(frame_id, found)
    depth = relative_from_output(outputs[0], int(state["spatial"]["preview_max_side"]))
    del outputs
    return depth_event(frame_id, depth)


def _infer_depth(state: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
    frame_id = str(message["frame_id"])
    try:
        depth_m, focal = _predict(state, message)
    except EngineError as exc:
        return {"event": "error", "code": exc.spec.code, "detail": exc.detail or ""}
    except Exception as exc:  # noqa: BLE001 - inferensi tidak boleh mematikan pekerja
        return {"event": "error", "code": "MDL-002", "detail": str(exc)}
    _keep_tensor(state, depth_m, focal, frame_id)
    side = int(state["spatial"]["preview_max_side"])
    return depth_event(frame_id, relative_preview(depth_m, side))


def _geometry(state: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
    if state.get("runtime") != "depth_pro":
        return {
            "event": "error",
            "code": "MDL-002",
            "detail": "pratinjau ONNX relatif tidak punya tensor meter",
        }
    try:
        depth_m, focal = _predict(state, message)
        result = scene_from_message(depth_m, focal, message)
    except EngineError as exc:
        return {"event": "error", "code": exc.spec.code, "detail": exc.detail or ""}
    except (ValueError, KeyError, TypeError) as exc:
        return {"event": "error", "code": "MDL-002", "detail": str(exc)}
    except Exception as exc:  # noqa: BLE001 - inferensi tidak boleh mematikan pekerja
        return {"event": "error", "code": "MDL-002", "detail": str(exc)}
    _keep_tensor(state, depth_m, focal, str(message.get("frame_id")))
    return {"event": "result", "kind": "spatial-geometry", **result}


def _predict(state: dict[str, Any], message: dict[str, Any]) -> tuple[Any, float | None]:
    np = importlib.import_module("numpy")
    width, height = int(message["width"]), int(message["height"])
    image = np.frombuffer(_read_raw(message), dtype=np.uint8).reshape(height, width, 3)
    return infer_meters(state["depth_pro"], image)


def _keep_tensor(state: dict[str, Any], depth_m: Any, focal: float | None, frame_id: str) -> None:
    state["tensor"] = depth_m
    state["focal"] = focal
    state["tensor_frame"] = frame_id


def _place_hydro(model: Any, device: str, message: dict[str, Any], imgsz: int) -> str:
    if device == "cpu":
        return cpu_fallback_note()
    return prepare_detector(
        model,
        device,
        float(message.get("vram_budget_mb") or 0),
        float(message.get("gpu_max_pct") or 90),
        imgsz,
    )


def _load_imgsz(message: dict[str, Any]) -> int:
    value = message.get("imgsz")
    if isinstance(value, int) and value in QUALITY_SIZES:
        return value
    return IMGSZ


def _tune_confidence(message: dict[str, Any]) -> float | None:
    value = message.get("confidence")
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _tune_imgsz(message: dict[str, Any]) -> int:
    value = message.get("imgsz")
    if isinstance(value, int) and value in QUALITY_SIZES:
        return value
    return IMGSZ


def _read_raw(message: dict[str, Any]) -> bytes:
    from multiprocessing.shared_memory import SharedMemory

    shared = SharedMemory(name=str(message["shm"]))
    try:
        width, height = int(message["width"]), int(message["height"])
        view: Any = shared.buf
        return bytes(view[: width * height * 3])
    finally:
        shared.close()


def _tensor(np: Any, raw: bytes, width: int, height: int, meta: dict[str, Any]) -> Any:
    image = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 3)
    net_h = int(meta["height"] or height)
    net_w = int(meta["width"] or width)
    if net_h != height or net_w != width:
        cv2 = importlib.import_module("cv2")
        image = cv2.resize(image, (net_w, net_h))
    rgb = image[:, :, ::-1].astype(np.float32) / 255.0
    batch = np.transpose(rgb, (2, 0, 1))[None, ...]
    if meta.get("fp16"):
        batch = batch.astype(np.float16)
    return batch


def _write_aquaclear(state: dict[str, Any], message: dict[str, Any]) -> tuple[int, int]:
    from multiprocessing.shared_memory import SharedMemory

    shared = SharedMemory(name=str(message["shm"]))
    try:
        width, height = int(message["width"]), int(message["height"])
        view: Any = shared.buf
        raw = bytes(view[: width * height * 3])
        enhancer = state.get("enhancer")
        if enhancer is None:
            enhancer, _note = open_enhancer(
                state["preset"],
                int(state.get("max_side") or 0),
                float(state.get("vram_budget_mb") or 0),
                float(state.get("gpu_max_pct") or 90),
            )
            state["enhancer"] = enhancer
        out, out_w, out_h = enhance_live(
            enhancer, raw, width, height, int(state.get("max_side") or 0)
        )
        view[: len(out)] = out
        return out_w, out_h
    finally:
        shared.close()


def _hold_if_requested() -> None:
    if os.environ.get("DEEPINSIGHT_WORKER_HOLD") == "1":
        time.sleep(30)


def _emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
