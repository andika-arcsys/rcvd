"""Tab Ukur: panjang, lebar, luas, posisi jam. Rumus (M.1) sampai (M.5)."""

from __future__ import annotations

from typing import Any

import numpy as np

from .camera import PipeCamera


def axis_param(r: Any, c: Any, d: Any) -> float:
    """Parameter t titik sumbu terdekat ke sinar r. Rumus (M.1)."""
    rv, cv, dv = (np.asarray(x, dtype=np.float64) for x in (r, c, d))
    a, bc, e = dv @ dv, dv @ rv, rv @ rv
    return float((bc * (rv @ cv) - e * (dv @ cv)) / (a * e - bc**2))


def length_along_axis(cam: PipeCamera, p1: Any, p2: Any, c: Any, d: Any) -> float:
    r1, r2 = cam.rays([p1, p2])
    return abs(axis_param(r2, c, d) - axis_param(r1, c, d))


def ray_cylinder(r: Any, c: Any, d: Any, radius: float) -> float | None:
    """Akar positif terkecil persamaan kuadrat sinar-silinder. Rumus (M.2)."""
    rv, cv, dv = (np.asarray(x, dtype=np.float64) for x in (r, c, d))
    w = -cv
    rp = rv - (rv @ dv) * dv
    wp = w - (w @ dv) * dv
    a = rp @ rp
    b = 2 * (rp @ wp)
    cc = wp @ wp - radius**2
    disc = b * b - 4 * a * cc
    if disc < 0 or a < 1e-12:
        return None
    roots = sorted([(-b - np.sqrt(disc)) / (2 * a), (-b + np.sqrt(disc)) / (2 * a)])
    positive = [x for x in roots if x > 0]
    return float(positive[0]) if positive else None


def up_vector(pitch_deg: float) -> np.ndarray:
    """Arah atas dunia di koordinat kamera. Rumus (M.5)."""
    t = np.radians(pitch_deg)
    return np.array([0.0, -np.cos(t), np.sin(t)])


def basis(d: Any, g_up: Any) -> tuple[np.ndarray, np.ndarray]:
    dv = np.asarray(d, dtype=np.float64)
    up = np.asarray(g_up, dtype=np.float64)
    e1 = up - (up @ dv) * dv
    e1 = e1 / np.linalg.norm(e1)
    return e1, np.cross(dv, e1)


def to_cyl(p: Any, c: Any, d: Any, e1: Any, e2: Any) -> tuple[float, float]:
    """Koordinat silinder (t, phi). Rumus (M.3)."""
    q = np.asarray(p, dtype=np.float64) - np.asarray(c, dtype=np.float64)
    return float(q @ np.asarray(d)), float(np.arctan2(q @ np.asarray(e2), q @ np.asarray(e1)))


def clock(phi: float) -> int:
    hour = (np.degrees(phi) / 30.0) % 12
    return 12 if round(hour) % 12 == 0 else int(round(hour))


def surface_point(cam: PipeCamera, p: Any, c: Any, d: Any, radius: float) -> np.ndarray:
    r = cam.rays([p])[0]
    lam = ray_cylinder(r, c, d, radius)
    if lam is None:
        raise ValueError("Titik di luar pipa.")
    return np.asarray(lam * r)


def unroll(
    cam: PipeCamera, pts_px: Any, c: Any, d: Any, radius: float, e1: Any, e2: Any
) -> np.ndarray:
    """Titik permukaan ke bidang terbentang (t, R*phi)."""
    out = []
    for p in np.asarray(pts_px, dtype=np.float64).reshape(-1, 2):
        t, phi = to_cyl(surface_point(cam, p, c, d, radius), c, d, e1, e2)
        out.append((t, radius * phi))
    return np.array(out)


def surface_width(xy: np.ndarray) -> float:
    return float(np.linalg.norm(xy[1] - xy[0]))


def area(xy: np.ndarray) -> float:
    """Shoelace pada permukaan terbentang. Rumus (M.4)."""
    x, y = xy[:, 0], xy[:, 1]
    return float(0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y)))
