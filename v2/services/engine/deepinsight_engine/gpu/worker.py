"""Proses pekerja: satu model. AquaClear di CPU. ONNX hanya dibuka bila berkasnya ada."""

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
from .aquaclear import apply_preset
from .depth_map import relative_from_output
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
        elif command == "unload":
            _hold_if_requested()
            state["session"] = None
            state["classes"] = None
            state["hydro"] = None
            _emit({"event": "unloaded"})


def _load(state: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
    kind = str(message["kind"])
    root = Path(str(message["models_dir"]))
    missing = _missing_file(kind, root, message)
    if missing:
        return {"event": "error", "code": "MDL-001", "detail": missing}
    if kind == "aquaclear":
        state["preset"] = AquaPreset.model_validate(message["preset"])
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
    return {"event": "ready", "fp16": bool(state.get("meta", {}).get("fp16"))}


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
        _write_aquaclear(message, state["preset"])
        return {
            "event": "result",
            "frame_id": message["frame_id"],
            "enhanced": True,
            "kind": "aquaclear",
        }
    if state["session"] is None:
        return {"event": "error", "code": "MDL-002", "detail": "sesi model kosong"}
    try:
        return _infer_onnx(state, message)
    except EngineError as exc:
        return {"event": "error", "code": exc.spec.code, "detail": exc.detail or ""}


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


def _write_aquaclear(message: dict[str, Any], preset: AquaPreset) -> None:
    from multiprocessing.shared_memory import SharedMemory

    shared = SharedMemory(name=str(message["shm"]))
    try:
        width, height = int(message["width"]), int(message["height"])
        view: Any = shared.buf
        raw = bytes(view[: width * height * 3])
        out = apply_preset(raw, width, height, preset)
        view[: len(out)] = out
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
