"""Membaca berkas, kamera USB, atau RTSP. Gagal buka berarti VID-003."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

from ..core.errors import EngineError


def _cv2() -> Any:
    try:
        return importlib.import_module("cv2")
    except ImportError as exc:
        raise EngineError("MDL-002", "opencv belum terpasang") from exc


def read_file(path: Path, limit: int) -> list[tuple[int, int, bytes]]:
    if limit < 1:
        raise EngineError("API-002", "limit frame")
    capture = _cv2().VideoCapture(str(path))
    if not capture.isOpened():
        raise EngineError("VID-003", str(path))
    frames: list[tuple[int, int, bytes]] = []
    try:
        frames = _collect(capture, limit)
    finally:
        capture.release()
    if not frames:
        raise EngineError("VID-003", "berkas tidak berisi frame")
    return frames


def _collect(capture: Any, limit: int) -> list[tuple[int, int, bytes]]:
    frames: list[tuple[int, int, bytes]] = []
    while len(frames) < limit:
        ok, image = capture.read()
        if not ok:
            break
        height, width = int(image.shape[0]), int(image.shape[1])
        frames.append((width, height, bytes(image.tobytes())))
    return frames


def open_live(
    kind: str,
    path: str | None = None,
    device_index: int | None = None,
    rtsp_url: str | None = None,
) -> Any:
    """Buka VideoCapture. Melempar VID-003 bila target kosong atau tidak dapat dibuka."""
    capture = _open(kind, _target(kind, path, device_index, rtsp_url))
    if not capture.isOpened():
        capture.release()
        raise EngineError("VID-003", kind)
    return capture


def read_one(capture: Any) -> tuple[int, int, bytes] | None:
    if capture is None:
        return None
    ok, image = capture.read()
    if not ok:
        return None
    height, width = int(image.shape[0]), int(image.shape[1])
    return width, height, bytes(image.tobytes())


def _open(kind: str, target: str | int) -> Any:
    cv2 = _cv2()
    if kind == "camera" and sys.platform == "win32":
        return cv2.VideoCapture(target, cv2.CAP_DSHOW)
    return cv2.VideoCapture(target)


def _target(
    kind: str, path: str | None, device_index: int | None, rtsp_url: str | None
) -> str | int:
    if kind == "file":
        if not path:
            raise EngineError("VID-003", "file")
        return path
    if kind == "camera":
        if device_index is None:
            raise EngineError("VID-003", "camera")
        return int(device_index)
    if kind == "rtsp":
        if not rtsp_url:
            raise EngineError("VID-003", "rtsp")
        return rtsp_url
    raise EngineError("API-002", kind)
