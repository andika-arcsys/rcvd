"""CAL 3: stasiun diameter, jarak kamera ke sumbu, sumbu 3D. Rumus (C3.1) sampai (C3.7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .angles import mean_axial
from .cal2 import fit_line, line_y, local_dirs, vanishing
from .camera import PipeCamera

RESIDUAL_LIMIT = 0.02
ANGLE_LIMIT_DEG = 3.0
SPREAD_MIN = 0.5
MIN_STATIONS = 3


@dataclass(frozen=True)
class Station:
    q: np.ndarray
    rho: float
    alpha: float
    width_px: float
    mid: np.ndarray


def station_ud(cam: PipeCamera, p_top: Any, p_bot: Any, radius: float) -> Station:
    """Stasiun dari dua titik tepi yang sudah bebas distorsi."""
    rt, rb = cam.rays_ud([p_top, p_bot])
    alpha = 0.5 * float(np.arccos(np.clip(rt @ rb, -1, 1)))  # Rumus (C3.1)
    rho = radius / np.sin(alpha)  # Rumus (C3.2)
    bis = rt + rb
    bis = bis / np.linalg.norm(bis)
    q = rho * bis  # Rumus (C3.3)
    top = np.asarray(p_top, dtype=np.float64)
    bot = np.asarray(p_bot, dtype=np.float64)
    return Station(q, float(rho), alpha, float(np.linalg.norm(top - bot)), (top + bot) / 2)


def station(cam: PipeCamera, p_top: Any, p_bot: Any, radius: float) -> Station:
    """Stasiun dari klik mentah (piksel frame asli)."""
    top, bot = cam.undistort_px([p_top, p_bot])
    return station_ud(cam, top, bot, radius)


def line_hit(line: np.ndarray, p: np.ndarray, n: np.ndarray) -> np.ndarray | None:
    den = float(line[:2] @ n)
    if abs(den) < 1e-12:
        return None
    t = -(float(line[:2] @ p) + line[2]) / den
    return np.asarray(p + t * n)


def clip_range(line: np.ndarray, width: int, height: int) -> tuple[float, float] | None:
    """Rentang u garis yang masih berada di dalam frame."""
    if abs(line[1]) < 1e-12:
        return None
    ys = [line_y(line, 0.0), line_y(line, float(width))]
    if ys[0] is None or ys[1] is None:
        return None
    lo, hi = 0.0, float(width)
    if abs(ys[1] - ys[0]) > 1e-12:
        slope = (ys[1] - ys[0]) / width
        u_a = (0.0 - ys[0]) / slope
        u_b = (height - ys[0]) / slope
        lo = max(lo, min(u_a, u_b))
        hi = min(hi, max(u_a, u_b))
    elif not 0 <= ys[0] <= height:
        return None
    return (lo, hi) if hi > lo else None


def auto_stations(
    l_top: np.ndarray,
    l_bot: np.ndarray,
    vp: np.ndarray,
    u_range: tuple[float, float],
    step: float = 100.0,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Pasangan titik tiap `step` piksel. Tombol Otomatis."""
    out: list[tuple[np.ndarray, np.ndarray]] = []
    for u in np.arange(u_range[0], u_range[1] + 1e-9, step):
        v = line_y(l_top, float(u))
        if v is None:
            continue
        p = np.array([u, v])
        _, n = local_dirs(p, vp)
        hit = line_hit(l_bot, p, n)
        if hit is not None:
            out.append((p, hit))
    return out


def fit_axis(stations: list[Station]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Titik pusat, arah d, galat relatif tiap stasiun. Rumus (C3.4) dan (C3.5)."""
    q = np.array([s.q for s in stations])
    centre = q.mean(axis=0)
    _, _, vt = np.linalg.svd(q - centre)
    d = vt[0]
    if d[2] < 0:
        d = -d
    rho = np.array([s.rho for s in stations])
    e = np.linalg.norm(np.cross(q - centre, d), axis=1) / rho
    return centre, d, e


def width_regression(s_pos: Any, widths: Any) -> tuple[np.ndarray, np.ndarray]:
    """Regresi linear lebar tampak terhadap posisi. Rumus (C3.6) dan (A1.9)."""
    s = np.asarray(s_pos, dtype=np.float64)
    w = np.asarray(widths, dtype=np.float64)
    a = np.vstack([np.ones_like(s), s]).T
    beta, *_ = np.linalg.lstsq(a, w, rcond=None)
    pred = a @ beta
    return beta, np.abs(w - pred) / np.where(np.abs(pred) < 1e-9, 1e-9, pred)


def axis_agreement(d_fit: Any, d_vp: Any) -> float:
    """Sudut antara d hasil fit dan d dari titik hilang. Rumus (C3.6)."""
    return float(np.degrees(np.arccos(min(1.0, abs(float(np.dot(d_fit, d_vp)))))))


def locked_tool(p0: Any, mouse: Any, n: Any) -> tuple[np.ndarray, float]:
    """Garis diameter terkunci tegak lurus sumbu lokal. Rumus (C3.7)."""
    p = np.asarray(p0, dtype=np.float64)
    length = float((np.asarray(mouse, dtype=np.float64) - p) @ np.asarray(n, dtype=np.float64))
    return p + length * np.asarray(n, dtype=np.float64), abs(length)


def cal3_pass(
    n_stations: int, e: np.ndarray, rel_res: np.ndarray, ang: float, spread: float
) -> bool:
    return bool(
        n_stations >= MIN_STATIONS
        and e.max() < RESIDUAL_LIMIT
        and rel_res.max() < RESIDUAL_LIMIT
        and ang < ANGLE_LIMIT_DEG
        and spread > SPREAD_MIN
    )


@dataclass
class Silhouettes:
    l_top: np.ndarray
    l_bot: np.ndarray
    res_top: float
    res_bot: float
    vp: np.ndarray
    d_vp: np.ndarray
    psi: float
    top_ud: np.ndarray
    bot_ud: np.ndarray


def silhouettes(cam: PipeCamera, top_raw: Any, bot_raw: Any) -> Silhouettes:
    top = cam.undistort_px(top_raw)
    bot = cam.undistort_px(bot_raw)
    l_top, res_top, _ = fit_line(top)
    l_bot, res_bot, _ = fit_line(bot)
    vp, d_vp, psi = vanishing(l_top, l_bot, cam.K)
    return Silhouettes(l_top, l_bot, res_top, res_bot, vp, d_vp, psi, top, bot)


@dataclass
class AxisModel:
    c: np.ndarray
    d: np.ndarray
    stations: list[Station]
    e: np.ndarray
    rel_res: np.ndarray
    beta: np.ndarray
    angle_deg: float
    spread: float
    passed: bool
    s_pos: np.ndarray = field(default_factory=lambda: np.zeros(0))


def axis_model(
    cam: PipeCamera,
    sil: Silhouettes,
    pairs_ud: list[tuple[np.ndarray, np.ndarray]],
    radius: float,
) -> AxisModel:
    stations = [station_ud(cam, a, b, radius) for a, b in pairs_ud]
    if len(stations) < 2:
        raise ValueError("Sumbu 3D butuh minimal 2 stasiun.")
    c, d, e = fit_axis(stations)
    unit = _image_axis(sil)
    mids = np.array([s.mid for s in stations])
    s_pos = (mids - mids[0]) @ unit
    beta, rel_res = width_regression(s_pos, [s.width_px for s in stations])
    angle = axis_agreement(d, sil.d_vp)
    spread = _spread(sil, cam.size, s_pos, unit)
    ok = cal3_pass(len(stations), e, rel_res, angle, spread)
    return AxisModel(c, d, stations, e, rel_res, beta, angle, spread, ok, s_pos)


def _image_axis(sil: Silhouettes) -> np.ndarray:
    angles = [np.degrees(np.arctan2(-line[0], line[1])) for line in (sil.l_top, sil.l_bot)]
    mean, _ = mean_axial(angles)
    rad = np.radians(mean)
    return np.array([np.cos(rad), np.sin(rad)])


def _spread(sil: Silhouettes, size: tuple[int, int], s_pos: np.ndarray, unit: np.ndarray) -> float:
    clip = clip_range(sil.l_top, size[0], size[1])
    if clip is None:
        return 0.0
    visible = (clip[1] - clip[0]) / max(abs(unit[0]), 1e-9)
    return float((s_pos.max() - s_pos.min()) / visible) if visible > 0 else 0.0
