"""Pratinjau relatif dari tensor kedalaman. Dekat = 1, jauh = 0. Bukan meter.

Gambar warna memakai Turbo seperti konsol: dekat hangat, jauh dingin, rentang
persentil 2–98. Itu peta yang sama dengan penampil Depth Anything, bukan
campuran hijau–magenta.
"""

from __future__ import annotations

import base64
import importlib
from typing import Any

from ..gpu.vision import RELATIVE_LABEL

COLOR_SIDE = 640


def relative_preview(depth_m: Any, max_side: int) -> dict[str, object]:
    np = importlib.import_module("numpy")
    data = np.asarray(depth_m, dtype="float32")
    height, width = int(data.shape[0]), int(data.shape[1])
    nearness = _nearness(np, data)
    step = _stride(width, height, max_side)
    values = _sample(nearness, width, height, step)
    row: dict[str, object] = {
        "width": len(range(0, width, step)),
        "height": len(range(0, height, step)),
        "values": values,
        "label": RELATIVE_LABEL,
    }
    jpeg = _turbo_jpeg(np, data)
    if jpeg:
        row["jpeg_b64"] = jpeg
    return row


def turbo_bgr(depth_m: Any) -> Any:
    """BGR uint8. Dekat = merah Turbo, jauh = biru. Sama dengan ``web/app.py``."""
    np = importlib.import_module("numpy")
    cv2 = importlib.import_module("cv2")
    data = np.asarray(depth_m, dtype="float32")
    valid = data[np.isfinite(data) & (data > 0)]
    if valid.size < 16:
        return np.zeros((*data.shape, 3), dtype=np.uint8)
    near, far = np.percentile(valid, (2, 98))
    normalized = np.clip((data - near) / max(float(far - near), 1e-6), 0, 1)
    image = ((1.0 - normalized) * 255).astype(np.uint8)
    return cv2.applyColorMap(image, cv2.COLORMAP_TURBO)


def _nearness(np: Any, data: Any) -> Any:
    valid = data[np.isfinite(data) & (data > 0)]
    if valid.size < 16:
        low = float(np.nanmin(data))
        high = float(np.nanmax(data))
    else:
        low = float(np.percentile(valid, 2))
        high = float(np.percentile(valid, 98))
    span = max(high - low, 1e-6)
    clipped = np.clip((data - low) / span, 0, 1)
    return np.round(1.0 - clipped, 4)


def _stride(width: int, height: int, max_side: int) -> int:
    longest = max(width, height)
    if longest <= max_side:
        return 1
    return max(1, -(-longest // max_side))


def _turbo_jpeg(np: Any, depth_m: Any) -> str | None:
    try:
        cv2 = importlib.import_module("cv2")
    except ImportError:
        return None
    colored = turbo_bgr(depth_m)
    height, width = int(colored.shape[0]), int(colored.shape[1])
    longest = max(height, width)
    if longest > COLOR_SIDE:
        scale = COLOR_SIDE / float(longest)
        colored = cv2.resize(
            colored,
            (max(1, int(width * scale)), max(1, int(height * scale))),
            interpolation=cv2.INTER_AREA,
        )
    ok, encoded = cv2.imencode(".jpg", colored, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ok:
        return None
    return base64.b64encode(np.asarray(encoded).tobytes()).decode("ascii")


def _sample(values: Any, width: int, height: int, step: int) -> list[float]:
    sampled: list[float] = []
    for y in range(0, height, step):
        for x in range(0, width, step):
            sampled.append(float(values[y, x]))
    return sampled
