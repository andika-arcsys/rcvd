"""Penyelarasan kedalaman model terhadap Z ArUco.

Satu pengali k pada seluruh peta tidak mengubah rasio antar garis, karena
skala garis referensi pada frame yang sama ikut terkalikan. Yang disimpan
adalah garis Z_fisik = a·Z_model + b dari sedikitnya dua jarak yang berbeda.
Nilai a dan b hanya ditulis dari pasangan yang terukur, tidak dari tebakan.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_MIN_SPAN = 1e-4


@dataclass(frozen=True)
class Alignment:
    a: float
    b: float
    samples: int


def ratio(z_physical_m: float, z_model_m: float) -> float | None:
    """k = Z_fisik / Z_model pada satu titik. None bila pembagi tidak sah."""
    if z_physical_m <= 0 or z_model_m <= 0:
        return None
    return z_physical_m / z_model_m


def fit_affine(pairs: list[tuple[float, float]]) -> tuple[float, float] | None:
    """Kuadrat terkecil Z_fisik = a·Z_model + b. Pasangan adalah (Z_model, Z_fisik)."""
    usable = [(x, y) for x, y in pairs if x > 0 and y > 0]
    if len(usable) < 2:
        return None
    xs = [item[0] for item in usable]
    if max(xs) - min(xs) < _MIN_SPAN:
        return None
    count = float(len(usable))
    sum_x = sum(xs)
    sum_y = sum(item[1] for item in usable)
    sum_xx = sum(item * item for item in xs)
    sum_xy = sum(x * y for x, y in usable)
    det = count * sum_xx - sum_x * sum_x
    if abs(det) < 1e-12:
        return None
    slope = (count * sum_xy - sum_x * sum_y) / det
    bias = (sum_y - slope * sum_x) / count
    if slope <= 0:
        return None
    return float(slope), float(bias)


def apply_alignment(depth: Any, slope: float, bias: float) -> Any:
    import numpy as np

    return np.asarray(depth, dtype=np.float64) * float(slope) + float(bias)


def load_alignment(path: Path) -> Alignment | None:
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(loaded, dict):
        return None
    slope, bias = loaded.get("a"), loaded.get("b")
    samples = loaded.get("samples")
    count = len(samples) if isinstance(samples, list) else 0
    if not isinstance(slope, int | float) or isinstance(slope, bool):
        return None
    if not isinstance(bias, int | float) or isinstance(bias, bool):
        return None
    if float(slope) <= 0:
        return None
    return Alignment(a=float(slope), b=float(bias), samples=count)


def record_pair(path: Path, camera_id: str, z_model_m: float, z_pnp_m: float) -> Alignment | None:
    """Tambah satu pasangan mentah. Profil a, b ditulis bila pasangan cukup beragam."""
    if z_model_m <= 0 or z_pnp_m <= 0:
        return load_alignment(path)
    previous = _read(path)
    samples = [*previous, {"z_model_m": z_model_m, "z_pnp_m": z_pnp_m}][-12:]
    fitted = fit_affine([(float(item["z_model_m"]), float(item["z_pnp_m"])) for item in samples])
    body: dict[str, object] = {
        "schema_version": 1,
        "camera_id": camera_id,
        "samples": samples,
        "a": None if fitted is None else fitted[0],
        "b": None if fitted is None else fitted[1],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2), encoding="utf-8")
    if fitted is None:
        return None
    return Alignment(a=fitted[0], b=fitted[1], samples=len(samples))


def alignment_note(slope: float, bias: float) -> str:
    return (
        f"Profil K3 Z = {slope:.4f}·Z_model + {bias:.4f} m. "
        "Rasio gradasi 1.50 tidak dipakai pada frame ini."
    )


@dataclass(frozen=True)
class AlignmentStatus:
    a: float | None
    b: float | None
    samples: int


def alignment_status(path: Path) -> AlignmentStatus:
    rows = _read(path)
    fitted = load_alignment(path)
    if fitted is None:
        return AlignmentStatus(None, None, len(rows))
    return AlignmentStatus(fitted.a, fitted.b, len(rows))


def observe_and_record(
    path: Path,
    camera_id: str,
    image: Any,
    depth: Any,
    camera_matrix: list[float],
    dist_coeffs: list[float],
    marker_mm: float,
    dictionary_name: str = "DICT_4X4_50",
) -> Alignment | None:
    """Catat satu pasangan dari foto mentah. Gagal diam-diam lewat None."""
    import importlib

    from .aruco_depth import measure_markers

    cv2: Any = importlib.import_module("cv2")
    ok, encoded = cv2.imencode(".jpg", image)
    if not ok:
        return None
    scan = measure_markers(bytes(encoded), camera_matrix, dist_coeffs, marker_mm, dictionary_name)
    if not scan.markers:
        return None
    pose = scan.markers[0]
    height, width = int(image.shape[0]), int(image.shape[1])
    z_model = sample_depth(depth, pose.center_u, pose.center_v, width, height)
    if z_model is None:
        return None
    return record_pair(path, camera_id, z_model, pose.z_mm / 1000.0)


def sample_depth(
    depth: Any, u: float, v: float, image_width: int, image_height: int
) -> float | None:
    import numpy as np

    array = np.asarray(depth, dtype=np.float64)
    if array.ndim < 2 or image_width < 1 or image_height < 1:
        return None
    x = int(round(u * array.shape[1] / image_width))
    y = int(round(v * array.shape[0] / image_height))
    y0, y1 = max(0, y - 2), min(array.shape[0], y + 3)
    x0, x1 = max(0, x - 2), min(array.shape[1], x + 3)
    window = array[y0:y1, x0:x1]
    valid = window[np.isfinite(window) & (window > 0)]
    if valid.size == 0:
        return None
    return float(np.median(valid))


def _read(path: Path) -> list[dict[str, float]]:
    if not path.is_file():
        return []
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = loaded.get("samples") if isinstance(loaded, dict) else None
    if not isinstance(rows, list):
        return []
    kept: list[dict[str, float]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        model, physical = item.get("z_model_m"), item.get("z_pnp_m")
        if isinstance(model, int | float) and isinstance(physical, int | float):
            kept.append({"z_model_m": float(model), "z_pnp_m": float(physical)})
    return kept
