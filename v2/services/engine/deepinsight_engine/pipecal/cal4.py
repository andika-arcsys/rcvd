"""CAL 4: selaraskan peta kedalaman model ke silinder 3D. Rumus (C4.1) sampai (C4.4)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from .camera import PipeCamera
from .measure import ray_cylinder

KINDS = ("disparity", "depth")
FIT_ERR_PASS = 0.05
MIN_POINTS = 50


@dataclass(frozen=True)
class DepthFit:
    a: float
    b: float
    error: float
    points: int
    sigma_cm: float
    kind: str


def load_tensor(raw: bytes) -> np.ndarray:
    """Tensor float mentah dari .npy. Peta berwarna tidak diterima."""
    import io

    try:
        arr = np.load(io.BytesIO(raw), allow_pickle=False)
    except (ValueError, OSError) as exc:
        raise ValueError("Berkas bukan .npy yang sah.") from exc
    arr = np.asarray(arr, dtype=np.float32)
    while arr.ndim > 2 and arr.shape[0] == 1:
        arr = arr[0]
    if arr.ndim != 2 or min(arr.shape) < 8:
        raise ValueError("Tensor harus peta 2 dimensi (tinggi × lebar).")
    if not np.isfinite(arr).any():
        raise ValueError("Tensor tidak berisi angka terhingga.")
    return np.asarray(arr, dtype=np.float32)


def sample(m: np.ndarray, u: float, v: float, w: int, h: int, win: int = 2) -> float:
    """Median 5×5 di koordinat tensor. Rumus (C4.1)."""
    ut = int(round(u * m.shape[1] / w))
    vt = int(round(v * m.shape[0] / h))
    ut = min(max(ut, 0), m.shape[1] - 1)
    vt = min(max(vt, 0), m.shape[0] - 1)
    patch = m[max(vt - win, 0) : vt + win + 1, max(ut - win, 0) : ut + win + 1]
    return float(np.median(patch))


def fit_ab(
    m_vals: Any, z_geo: Any, kind: str = "disparity", iters: int = 8
) -> tuple[float, float, float]:
    """IRLS dengan bobot Tukey. Rumus (C4.2) dan (C4.3)."""
    m = np.asarray(m_vals, dtype=np.float64)
    z = np.asarray(z_geo, dtype=np.float64)
    ok = np.isfinite(m) & np.isfinite(z) & (z > 0)
    m, z = m[ok], z[ok]
    if len(m) < 3 or np.ptp(m) < 1e-9:
        raise ValueError("Sebaran nilai model terlalu sempit untuk fit a, b.")
    a_mat = np.vstack([m, np.ones_like(m)]).T
    y = 1.0 / z if kind == "disparity" else z
    w = np.ones_like(y)
    coef = np.zeros(2)
    for _ in range(iters):
        coef, *_ = np.linalg.lstsq(a_mat * w[:, None], y * w, rcond=None)
        r = y - a_mat @ coef
        s = 1.4826 * np.median(np.abs(r)) + 1e-12
        w = np.clip(1 - (r / (4.685 * s)) ** 2, 0, None) ** 2
    a, b = float(coef[0]), float(coef[1])
    zhat = _zhat(a, b, m, kind)
    valid = np.isfinite(zhat) & (zhat > 0)
    if valid.sum() < 3:
        raise ValueError("Hasil fit tidak menghasilkan kedalaman positif.")
    err = float(np.median(np.abs(zhat[valid] - z[valid]) / z[valid]))
    return a, b, err


def _zhat(a: float, b: float, m: np.ndarray, kind: str) -> np.ndarray:
    lin = a * m + b
    if kind == "disparity":
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.asarray(1.0 / lin)
    return np.asarray(lin)


def collect_pairs(
    cam: PipeCamera,
    m: np.ndarray,
    c: Any,
    d: Any,
    radius: float,
    w: int,
    h: int,
    step: int = 8,
) -> tuple[np.ndarray, np.ndarray]:
    """Nilai model dan kedalaman geometrik di permukaan pipa yang terlihat."""
    mv: list[float] = []
    zv: list[float] = []
    for v in range(0, h, step):
        row = np.array([[u, v] for u in range(0, w, step)], dtype=np.float64)
        rays = cam.rays(row)
        for (u, vv), r in zip(row, rays, strict=True):
            lam = ray_cylinder(r, c, d, radius)
            if lam is None:
                continue
            mv.append(sample(m, float(u), float(vv), w, h))
            zv.append(float(lam * r[2]))
    return np.array(mv), np.array(zv)


def run_fit(
    cam: PipeCamera,
    m: np.ndarray,
    c: Any,
    d: Any,
    radius: float,
    kind: str = "disparity",
    step: int = 8,
) -> DepthFit:
    w, h = cam.size
    mv, zv = collect_pairs(cam, m, c, d, radius, w, h, step)
    if len(mv) < MIN_POINTS:
        raise ValueError("Terlalu sedikit piksel permukaan pipa. Periksa sumbu CAL 3.")
    a, b, err = fit_ab(mv, zv, kind)
    zhat = _zhat(a, b, mv, kind)
    good = np.isfinite(zhat) & (zhat > 0)
    sigma = float(np.std(zhat[good] - zv[good])) if good.any() else math.nan
    return DepthFit(a, b, err, len(mv), sigma, kind)


def profile(
    cam: PipeCamera,
    pts_px: Any,
    m: np.ndarray,
    fit: DepthFit,
    c: Any,
    d: Any,
    radius: float,
) -> dict[str, Any]:
    """Profil penampang terukur dan teoretis. Rumus (C4.4)."""
    w, h = cam.size
    pts = np.asarray(pts_px, dtype=np.float64).reshape(-1, 2)
    rays = cam.rays(pts)
    mvals = np.array([sample(m, float(u), float(v), w, h) for u, v in pts])
    z = _zhat(fit.a, fit.b, mvals, fit.kind)
    cv = np.asarray(c, dtype=np.float64)
    dv = np.asarray(d, dtype=np.float64)
    bad = ~np.isfinite(z) | (z <= 0)
    z_safe = np.where(bad, np.nan, z)
    pcloud = rays / rays[:, 2:3] * z_safe[:, None]
    delta = np.linalg.norm(np.cross(pcloud - cv, dv), axis=1) - radius
    theory = []
    for r in rays:
        lam = ray_cylinder(r, cv, dv, radius)
        theory.append(math.nan if lam is None else float(lam * r[2]))
    finite = z_safe[np.isfinite(z_safe)]
    relief = float(finite.max() - finite.min()) if len(finite) else math.nan
    limit = 3 * fit.sigma_cm if math.isfinite(fit.sigma_cm) else math.inf
    return {
        "z": [None if math.isnan(x) else float(x) for x in z_safe],
        "theory": [None if math.isnan(x) else x for x in theory],
        "delta": [None if math.isnan(x) else float(x) for x in delta],
        "relief_cm": None if math.isnan(relief) else relief,
        "target_cm": float(radius),
        "flagged": [i for i, x in enumerate(delta) if math.isfinite(x) and abs(x) > limit],
    }


def turbo_preview(m: np.ndarray) -> bytes:
    """Pratinjau berwarna untuk mata saja. Perhitungan memakai tensor float."""
    import cv2

    finite = m[np.isfinite(m)]
    lo, hi = np.percentile(finite, [2, 98])
    scaled = np.clip((np.nan_to_num(m, nan=lo) - lo) / max(hi - lo, 1e-9), 0, 1)
    colour = cv2.applyColorMap((scaled * 255).astype(np.uint8), cv2.COLORMAP_TURBO)
    ok, enc = cv2.imencode(".jpg", colour, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        raise ValueError("Pratinjau gagal dibuat.")
    return bytes(enc)
