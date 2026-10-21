"""Pemetaan piksel PNG ke peta Depth Anything 3.

Metode bawaan inferensi adalah ``upper_bound_resize``: sisi terpanjang menjadi
``process_res``, lalu tiap sisi dibulatkan ke kelipatan 14. Tidak ada crop dan
tidak ada padding pada metode itu. Metode ``*crop`` memotong tengah setelah
resize; offset itu dibatalkan sebelum peta dikembalikan ke ukuran PNG.

Rumus mengikuti ``InputProcessor`` resmi (piksel diukur dari pusat piksel):

    u_bound = (u + 0.5) * bound_w / orig_w - 0.5

Lalu resize kedua, atau pengurangan offset crop.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

PATCH = 14
PROCESS_METHOD = "upper_bound_resize"


@dataclass(frozen=True)
class ProcessGeometry:
    orig_w: int
    orig_h: int
    bound_w: int
    bound_h: int
    proc_w: int
    proc_h: int
    crop_x: int
    crop_y: int
    method: str
    matched: bool = True


def process_geometry(
    width: int, height: int, process_res: int, method: str = PROCESS_METHOD
) -> ProcessGeometry:
    """Ukuran setelah resize batas dan setelah kelipatan 14. Sama dengan DA3."""
    bound_w, bound_h = _bound_size(width, height, process_res, method)
    if method.endswith("resize"):
        proc_w, proc_h = _nearest_patch(bound_w), _nearest_patch(bound_h)
        crop_x = crop_y = 0
    elif method.endswith("crop"):
        proc_w = max(PATCH, (bound_w // PATCH) * PATCH)
        proc_h = max(PATCH, (bound_h // PATCH) * PATCH)
        crop_x = (bound_w - proc_w) // 2
        crop_y = (bound_h - proc_h) // 2
    else:
        raise ValueError(f"process_res_method tidak dikenal: {method}")
    return ProcessGeometry(
        orig_w=width,
        orig_h=height,
        bound_w=bound_w,
        bound_h=bound_h,
        proc_w=proc_w,
        proc_h=proc_h,
        crop_x=crop_x,
        crop_y=crop_y,
        method=method,
    )


def map_png_to_proc(u: float, v: float, geom: ProcessGeometry) -> tuple[float, float]:
    """Koordinat PNG (u, v) ke koordinat peta yang diproses."""
    u_bound = (u + 0.5) * geom.bound_w / geom.orig_w - 0.5
    v_bound = (v + 0.5) * geom.bound_h / geom.orig_h - 0.5
    if geom.method.endswith("crop"):
        return u_bound - geom.crop_x, v_bound - geom.crop_y
    u_proc = (u_bound + 0.5) * geom.proc_w / geom.bound_w - 0.5
    v_proc = (v_bound + 0.5) * geom.proc_h / geom.bound_h - 0.5
    return u_proc, v_proc


def map_proc_to_png(u_proc: float, v_proc: float, geom: ProcessGeometry) -> tuple[float, float]:
    """Kebalikan map_png_to_proc. Pojok dan tengah kembali ke piksel yang sama."""
    if geom.method.endswith("crop"):
        u_bound = u_proc + geom.crop_x
        v_bound = v_proc + geom.crop_y
    else:
        u_bound = (u_proc + 0.5) * geom.bound_w / geom.proc_w - 0.5
        v_bound = (v_proc + 0.5) * geom.bound_h / geom.proc_h - 0.5
    u = (u_bound + 0.5) * geom.orig_w / geom.bound_w - 0.5
    v = (v_bound + 0.5) * geom.orig_h / geom.bound_h - 0.5
    return u, v


def align_map(values: Any, geom: ProcessGeometry, *, nearest: bool) -> Any:
    """Kembalikan peta proses ke ukuran PNG. Kedalaman linear, conf nearest."""
    np = importlib.import_module("numpy")
    grid = np.asarray(values, dtype=np.float32)
    if geom.crop_x or geom.crop_y:
        pad = np.float32(-1.0 if nearest else np.nan)
        bound = np.full((geom.bound_h, geom.bound_w), pad, dtype=np.float32)
        y0, x0 = geom.crop_y, geom.crop_x
        bound[y0 : y0 + geom.proc_h, x0 : x0 + geom.proc_w] = grid
        grid = bound
    if grid.shape[:2] == (geom.orig_h, geom.orig_w):
        return grid
    cv2 = importlib.import_module("cv2")
    interpolation = cv2.INTER_NEAREST if nearest else cv2.INTER_LINEAR
    return cv2.resize(grid, (geom.orig_w, geom.orig_h), interpolation=interpolation)


def scale_prediction_k(matrix: Any, geom: ProcessGeometry) -> tuple[float, float, float, float]:
    """Intrinsik DA3 (ukuran proses) menjadi piksel PNG."""
    np = importlib.import_module("numpy")
    k = np.asarray(matrix, dtype=np.float64)
    if k.ndim == 3:
        k = k[0]
    fx, fy, cx, cy = float(k[0, 0]), float(k[1, 1]), float(k[0, 2]), float(k[1, 2])
    if geom.method.endswith("crop"):
        cx += geom.crop_x
        cy += geom.crop_y
        sx = geom.orig_w / float(geom.bound_w)
        sy = geom.orig_h / float(geom.bound_h)
    else:
        sx = geom.orig_w / float(geom.proc_w)
        sy = geom.orig_h / float(geom.proc_h)
    return fx * sx, fy * sy, cx * sx, cy * sy


def camera_k(
    matrix: list[float],
    width: int,
    height: int,
    calib_w: int | None,
    calib_h: int | None,
) -> tuple[float, float, float, float]:
    """Matriks kalibrasi 3x3 baris-utama, diskalakan bila ukuran gambar berbeda."""
    fx, fy, cx, cy = float(matrix[0]), float(matrix[4]), float(matrix[2]), float(matrix[5])
    if calib_w and calib_h and (calib_w != width or calib_h != height):
        fx *= width / float(calib_w)
        cx *= width / float(calib_w)
        fy *= height / float(calib_h)
        cy *= height / float(calib_h)
    return fx, fy, cx, cy


def geometry_for_map(
    width: int,
    height: int,
    process_res: int,
    method: str,
    depth_shape: tuple[int, int],
) -> ProcessGeometry:
    """Pakai geometri resmi bila ukuran peta cocok. Jika tidak, regangkan penuh."""
    geom = process_geometry(width, height, process_res, method)
    if depth_shape == (geom.proc_h, geom.proc_w):
        return geom
    proc_h, proc_w = depth_shape
    return ProcessGeometry(
        orig_w=width,
        orig_h=height,
        bound_w=proc_w,
        bound_h=proc_h,
        proc_w=proc_w,
        proc_h=proc_h,
        crop_x=0,
        crop_y=0,
        method=method,
        matched=False,
    )


def _bound_size(width: int, height: int, process_res: int, method: str) -> tuple[int, int]:
    upper = method.startswith("upper")
    if not upper and not method.startswith("lower"):
        raise ValueError(f"process_res_method tidak dikenal: {method}")
    longest = max(width, height)
    shortest = min(width, height)
    if upper and longest == process_res:
        return width, height
    if not upper and shortest == process_res:
        return width, height
    side = longest if upper else shortest
    scale = process_res / float(side)
    return max(1, int(round(width * scale))), max(1, int(round(height * scale)))


def _nearest_patch(value: int) -> int:
    down = (value // PATCH) * PATCH
    up = down + PATCH
    chosen = up if abs(up - value) <= abs(value - down) else down
    return max(PATCH, chosen)
