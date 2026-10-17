"""Dekode YOLO-seg menjadi poligon dan RLE. Tensor dibuang sebelum fungsi kembali."""

from __future__ import annotations

import importlib
from typing import Any

from ..core.config import HydrodetectConfig
from ..core.errors import EngineError
from .vision import rle_encode, trim_candidates


def decode_yolo_seg(
    outputs: list[Any],
    classes: list[str],
    frame_w: int,
    frame_h: int,
    cfg: HydrodetectConfig,
) -> list[dict[str, object]]:
    np = importlib.import_module("numpy")
    pred, proto = _pair(outputs, np)
    rows = _rows(pred, proto, len(classes), np)
    candidates = [_one(np, row, proto, classes, frame_w, frame_h) for row in rows]
    del pred, proto, rows
    return trim_candidates([item for item in candidates if item], cfg)


def _pair(outputs: list[Any], np: Any) -> tuple[Any, Any]:
    arrays = [np.asarray(item) for item in outputs]
    pred = next((item for item in arrays if item.ndim == 3), None)
    proto = next((item for item in arrays if item.ndim == 4), None)
    if pred is None or proto is None:
        raise EngineError("MDL-002", "keluaran ONNX belum dikenali")
    return pred[0], proto[0]


def _rows(pred: Any, proto: Any, class_count: int, np: Any) -> list[Any]:
    mask_count = int(proto.shape[0])
    expect = 4 + class_count + mask_count
    if int(pred.shape[0]) == expect:
        table = pred.T
    elif int(pred.shape[1]) == expect:
        table = pred
    else:
        raise EngineError("MDL-002", "jumlah kanal tidak sesuai classes.json")
    return list(np.asarray(table))


def _one(
    np: Any,
    row: Any,
    proto: Any,
    classes: list[str],
    frame_w: int,
    frame_h: int,
) -> dict[str, object] | None:
    class_count = len(classes)
    mask_count = int(proto.shape[0])
    scores = row[4 : 4 + class_count]
    index = int(np.argmax(scores))
    score = float(scores[index])
    polygon, rle, size = _mask_geometry(np, row[4 + class_count :], proto, frame_w, frame_h)
    bbox = _bbox(row[:4], frame_w, frame_h, mask_count)
    del row
    if not polygon:
        return None
    return {
        "class_name": classes[index],
        "score": round(score, 4),
        "bbox": bbox,
        "polygon": polygon,
        "rle": rle,
        "rle_size": size,
    }


def _bbox(box: Any, frame_w: int, frame_h: int, _mask_count: int) -> list[int]:
    cx, cy, bw, bh = (float(box[0]), float(box[1]), float(box[2]), float(box[3]))
    if max(cx, cy, bw, bh) <= 1.5:
        cx, cy, bw, bh = cx * frame_w, cy * frame_h, bw * frame_w, bh * frame_h
    return [int(cx - bw / 2), int(cy - bh / 2), int(bw), int(bh)]


def _mask_geometry(
    np: Any,
    coeff: Any,
    proto: Any,
    frame_w: int,
    frame_h: int,
) -> tuple[list[list[int]], list[int], list[int]]:
    cv2 = importlib.import_module("cv2")
    flat = proto.reshape(int(proto.shape[0]), -1)
    raw = coeff.astype("float32") @ flat
    mask = 1.0 / (1.0 + np.exp(-np.clip(raw, -20, 20)))
    mask = mask.reshape(int(proto.shape[1]), int(proto.shape[2]))
    binary = (mask > 0.5).astype("uint8")
    del raw, mask
    size = [int(binary.shape[0]), int(binary.shape[1])]
    return _contour(cv2, binary, frame_w, frame_h), _rle(binary), size


def _rle(binary: Any) -> list[int]:
    rows = [[int(cell) for cell in row] for row in binary.tolist()]
    return rle_encode(rows)


def _contour(cv2: Any, binary: Any, frame_w: int, frame_h: int) -> list[list[int]]:
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return []
    contour = max(contours, key=cv2.contourArea)
    length = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.01 * length, True)
    mask_h, mask_w = int(binary.shape[0]), int(binary.shape[1])
    return [_point(pt[0], mask_w, mask_h, frame_w, frame_h) for pt in approx]


def _point(pt: Any, mask_w: int, mask_h: int, frame_w: int, frame_h: int) -> list[int]:
    x = int(round(float(pt[0]) * frame_w / mask_w))
    y = int(round(float(pt[1]) * frame_h / mask_h))
    return [x, y]
