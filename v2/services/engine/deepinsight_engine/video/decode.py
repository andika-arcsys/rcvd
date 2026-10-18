"""Membaca PNG bukti kembali menjadi piksel. Tidak mengubah berkas."""

from __future__ import annotations

import importlib
from typing import Any

from ..core.errors import EngineError


def decode_png(data: bytes) -> tuple[int, int, bytes]:
    cv2 = _cv2()
    np = importlib.import_module("numpy")
    array = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if array is None:
        raise EngineError("SYS-002", "PNG bukti tidak terbaca")
    height, width = int(array.shape[0]), int(array.shape[1])
    return width, height, bytes(array.tobytes())


def _cv2() -> Any:
    try:
        return importlib.import_module("cv2")
    except ImportError as exc:
        raise EngineError("MDL-002", "opencv belum terpasang") from exc
