"""CAL 2: siluet pipa, titik hilang, arah sumbu. Rumus (C2.1) sampai (C2.5)."""

from __future__ import annotations

from itertools import combinations
from typing import Any

import numpy as np

_EXHAUSTIVE_MAX = 12


def fit_line(pts: Any, iters: int = 200, tol: float = 1.5) -> tuple[np.ndarray, float, np.ndarray]:
    """RANSAC lalu kuadrat terkecil total. Mengembalikan l, RMS residual, penanda inlier."""
    points = np.asarray(pts, dtype=np.float64).reshape(-1, 2)
    if len(points) < 2:
        raise ValueError("Garis butuh minimal 2 titik.")
    inliers = _best_inliers(points, iters, tol)
    chosen = points[inliers]
    centre = chosen.mean(axis=0)
    _, _, vt = np.linalg.svd(chosen - centre)
    normal = vt[1]
    line = np.array([normal[0], normal[1], -normal @ centre])
    res = _residual(points, line)
    return line, float(np.sqrt((res[inliers] ** 2).mean())), inliers


def _residual(points: np.ndarray, line: np.ndarray) -> np.ndarray:
    # Rumus (C2.5)
    return np.asarray(np.abs(points @ line[:2] + line[2]) / np.hypot(line[0], line[1]))


def _best_inliers(points: np.ndarray, iters: int, tol: float) -> np.ndarray:
    count = len(points)
    if count == 2:
        return np.ones(2, dtype=bool)
    if count <= _EXHAUSTIVE_MAX:
        pairs = list(combinations(range(count), 2))
    else:
        rng = np.random.default_rng(0)
        pairs = [tuple(rng.choice(count, 2, replace=False)) for _ in range(iters)]
    best = np.ones(count, dtype=bool)
    best_n = -1
    for first, second in pairs:
        # Rumus (C2.1): garis dari dua titik homogen
        line = np.cross([*points[first], 1.0], [*points[second], 1.0])
        norm = float(np.hypot(line[0], line[1]))
        if norm < 1e-12:
            continue
        inl = _residual(points, line) < tol
        if int(inl.sum()) > best_n:
            best, best_n = inl, int(inl.sum())
    if best.sum() < 2:
        return np.ones(count, dtype=bool)
    return best


def vanishing(l_top: Any, l_bot: Any, K: Any) -> tuple[np.ndarray, np.ndarray, float]:
    """Titik hilang, arah sumbu d, sudut menjauh (derajat). Rumus (C2.1) dan (C2.2)."""
    vp = np.cross(l_top, l_bot)
    d = np.linalg.inv(np.asarray(K, dtype=np.float64)) @ vp
    d = d / np.linalg.norm(d)
    if d[2] < 0:
        d = -d
    psi = float(np.degrees(np.arcsin(min(1.0, abs(d[2])))))
    return vp, d, psi


def vp_pixel(vp: np.ndarray) -> tuple[float, float] | None:
    if abs(vp[2]) < 1e-9:
        return None
    return float(vp[0] / vp[2]), float(vp[1] / vp[2])


def local_dirs(p: Any, vp: Any) -> tuple[np.ndarray, np.ndarray]:
    """Arah sumbu lokal dan tegak lurusnya di titik p. Rumus (C2.3)."""
    vpv = np.asarray(vp, dtype=np.float64)
    if abs(vpv[2]) < 1e-9:
        a = vpv[:2].copy()
    else:
        a = vpv[:2] / vpv[2] - np.asarray(p, dtype=np.float64)
    a = a / np.linalg.norm(a)
    return a, np.array([-a[1], a[0]])


def snap_edge(gray: Any, p: Any, n: Any, half: int = 15) -> np.ndarray:
    """Geser titik ke gradien maksimum sepanjang n, parabola tiga titik. Rumus (C2.4)."""
    image = np.asarray(gray)
    t = np.arange(-half, half + 1)
    xs = p[0] + t * n[0]
    ys = p[1] + t * n[1]
    rows = np.clip(np.round(ys).astype(int), 0, image.shape[0] - 1)
    cols = np.clip(np.round(xs).astype(int), 0, image.shape[1] - 1)
    profile = image[rows, cols].astype(np.float64)
    g = np.abs(np.gradient(np.convolve(profile, np.ones(3) / 3, "same")))
    k = int(np.argmax(g[1:-1])) + 1
    den = g[k - 1] - 2 * g[k] + g[k + 1]
    delta = 0.5 * (g[k - 1] - g[k + 1]) / den if den != 0 else 0.0
    s = t[k] + delta
    return np.array([p[0] + s * n[0], p[1] + s * n[1]])


def line_y(line: np.ndarray, u: float) -> float | None:
    if abs(line[1]) < 1e-12:
        return None
    return float(-(line[0] * u + line[2]) / line[1])
