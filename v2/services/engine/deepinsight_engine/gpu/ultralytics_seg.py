"""HydroDetect dari bobot Ultralytics pada frame mentah.

Domain inferensi mengikuti pelatihan exp-5: citra BGR asli, bukan frame AquaClear.
ONNX tetap dipakai bila berkas .pt tidak ada.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from ..core.config import HydrodetectConfig
from ..core.errors import EngineError
from .vision import rle_encode, trim_candidates

IMGSZ = 640
QUALITY_SIZES = (640, 960, 1280)
_RLE_SIDE = 160


def hydro_source(root: Path, weights: str | None, onnx: str | None) -> tuple[str, Path] | None:
    """Utamakan .pt yang sudah dilatih. ONNX hanya cadangan."""
    if weights:
        path = root / weights
        if path.is_file():
            return ("ultralytics", path)
    if onnx:
        path = root / onnx
        if path.is_file():
            return ("onnx", path)
    return None


def missing_hydro_detail(weights: str | None, onnx: str | None) -> str:
    named = [item for item in (weights, onnx) if item]
    return " atau ".join(named) if named else "model.pt"


def load_yolo(path: Path) -> Any:
    try:
        yolo_cls = importlib.import_module("ultralytics").YOLO
    except ImportError as exc:
        raise EngineError("MDL-002", "ultralytics belum terpasang") from exc
    try:
        return yolo_cls(str(path))
    except Exception as exc:  # noqa: BLE001 - Ultralytics melempar error berkas yang beragam
        raise EngineError("MDL-002", "bobot Ultralytics tidak dapat dibuka") from exc


def names_of(model: Any) -> list[str]:
    raw = getattr(model, "names", None)
    if isinstance(raw, dict) and raw:
        ordered = [raw[key] for key in sorted(raw, key=lambda item: int(item))]
        return [str(item) for item in ordered]
    if isinstance(raw, list) and raw:
        return [str(item) for item in raw]
    raise EngineError("MDL-002", "nama kelas Ultralytics kosong")


def torch_device() -> str:
    try:
        torch = importlib.import_module("torch")
    except ImportError:
        return "cpu"
    if bool(torch.cuda.is_available()):
        return "0"
    return "cpu"


def predict_candidates(
    model: Any,
    image_bgr: Any,
    classes: list[str],
    cfg: HydrodetectConfig,
    device: str,
    confidence: float | None = None,
    imgsz: int = IMGSZ,
) -> list[dict[str, object]]:
    """Deteksi pada array BGR uint8.

    Tanpa angka keyakinan, ambang awal adalah ambang kelas terendah di berkas.
    Angka dari layar menggantikan ambang semua kelas dan ukuran gambar model.
    """
    gate = _floor(cfg) if confidence is None else confidence
    size = imgsz if imgsz in QUALITY_SIZES else IMGSZ
    result = model.predict(
        image_bgr,
        conf=gate,
        imgsz=size,
        device=device,
        retina_masks=True,
        verbose=False,
    )[0]
    height, width = int(image_bgr.shape[0]), int(image_bgr.shape[1])
    active = cfg if confidence is None else _uniform(cfg, confidence)
    return trim_candidates(_rows(result, classes, width, height), active)


def _uniform(cfg: HydrodetectConfig, confidence: float) -> HydrodetectConfig:
    return cfg.model_copy(update={"default_confidence": confidence, "overrides": {}})


def _floor(cfg: HydrodetectConfig) -> float:
    limits = [cfg.default_confidence, *cfg.overrides.values()]
    return min(limits) if limits else cfg.default_confidence


def _rows(result: Any, classes: list[str], width: int, height: int) -> list[dict[str, object]]:
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return []
    cls = _as_array(getattr(boxes, "cls", None))
    scores = _as_array(getattr(boxes, "conf", None))
    xyxy = _as_array(getattr(boxes, "xyxy", None))
    polygons = _polygons(result)
    if cls is None or scores is None or xyxy is None:
        return []
    found: list[dict[str, object]] = []
    for index in range(int(cls.shape[0])):
        class_index = int(cls[index])
        if class_index < 0 or class_index >= len(classes):
            continue
        polygon = _polygon_at(polygons, index, xyxy[index])
        item = _candidate(
            classes[class_index], float(scores[index]), xyxy[index], polygon, width, height
        )
        if item is not None:
            found.append(item)
    return found


def _candidate(
    name: str,
    score: float,
    box: Any,
    polygon: list[list[int]],
    width: int,
    height: int,
) -> dict[str, object] | None:
    if len(polygon) < 3:
        return None
    x1 = int(round(float(box[0])))
    y1 = int(round(float(box[1])))
    x2 = int(round(float(box[2])))
    y2 = int(round(float(box[3])))
    rle, size = _rle(polygon, width, height)
    return {
        "class_name": name,
        "score": round(score, 4),
        "bbox": [x1, y1, max(0, x2 - x1), max(0, y2 - y1)],
        "polygon": polygon,
        "rle": rle,
        "rle_size": size,
    }


def _polygons(result: Any) -> list[Any]:
    masks = getattr(result, "masks", None)
    xy = None if masks is None else getattr(masks, "xy", None)
    if xy is None:
        return []
    return list(xy)


def _polygon_at(polygons: list[Any], index: int, box: Any) -> list[list[int]]:
    if index < len(polygons):
        points = [[int(round(float(pt[0]))), int(round(float(pt[1])))] for pt in polygons[index]]
        if len(points) >= 3:
            return points
    x1, y1, x2, y2 = (float(box[0]), float(box[1]), float(box[2]), float(box[3]))
    return [
        [int(round(x1)), int(round(y1))],
        [int(round(x2)), int(round(y1))],
        [int(round(x2)), int(round(y2))],
        [int(round(x1)), int(round(y2))],
    ]


def _rle(polygon: list[list[int]], width: int, height: int) -> tuple[list[int], list[int]]:
    np = importlib.import_module("numpy")
    cv2 = importlib.import_module("cv2")
    longest = max(width, height, 1)
    scale = min(1.0, _RLE_SIDE / longest)
    mask_w = max(1, int(round(width * scale)))
    mask_h = max(1, int(round(height * scale)))
    mask = np.zeros((mask_h, mask_w), dtype=np.uint8)
    points = np.array([[int(x * scale), int(y * scale)] for x, y in polygon], dtype=np.int32)
    cv2.fillPoly(mask, [points], 1)
    rows = [[int(cell) for cell in row] for row in mask.tolist()]
    return rle_encode(rows), [mask_h, mask_w]


def _as_array(value: Any) -> Any | None:
    if value is None:
        return None
    np = importlib.import_module("numpy")
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    array = np.asarray(value)
    if getattr(array, "ndim", 0) == 0:
        return None
    return array
