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
from .aquaclear import apply_preset


def main() -> None:
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
        if isinstance(opened, str):
            return {"event": "error", "code": "MDL-002", "detail": opened}
        state["session"] = opened
    state["kind"] = kind
    return {"event": "ready"}


def _missing_file(kind: str, root: Path, message: dict[str, Any]) -> str | None:
    if kind == "aquaclear":
        return None
    for field in ("onnx", "classes"):
        relative = message.get(field)
        if relative and not (root / str(relative)).is_file():
            return str(relative)
    return None


def _open_session(path: Path) -> Any:
    try:
        ort = importlib.import_module("onnxruntime")
    except ImportError:
        return "onnxruntime belum terpasang"
    try:
        return ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    except Exception as exc:  # noqa: BLE001 - ORT melempar error khusus yang tidak diimpor
        return str(exc)


def _infer(state: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
    if state["kind"] == "aquaclear":
        _write_aquaclear(message, state["preset"])
        return {"event": "result", "frame_id": message["frame_id"], "enhanced": True}
    if state["session"] is None:
        return {"event": "error", "code": "MDL-002", "detail": "sesi model kosong"}
    return {"event": "result", "frame_id": message["frame_id"], "enhanced": False}


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
