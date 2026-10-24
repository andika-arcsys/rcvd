"""Ketidakpastian: propagasi galat dan Monte Carlo. Rumus (U.1) dan (U.2)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import numpy as np

DIAMETER_REL = {"pi-tape": 0.005, "coating": 0.03, "baja": 0.05}
F_REL = 0.005
EDGE_PX = 1.5


def analytic_rho(sf: float, sd: float, sl: float) -> float:
    # Rumus (U.1), nilai relatif
    return float(np.sqrt(sf**2 + sd**2 + sl**2))


def monte_carlo(
    measure_fn: Callable[[list[np.ndarray], float, float], float],
    edges: Sequence[Any],
    f_rel: float = F_REL,
    d_rel: float = 0.01,
    edge_px: float = EDGE_PX,
    n: int = 500,
    seed: int = 0,
) -> tuple[float, float, float, int]:
    """Median, P2.5, P97.5, dan jumlah putaran yang berhasil. Rumus (U.2)."""
    rng = np.random.default_rng(seed)
    out: list[float] = []
    base = [np.asarray(p, dtype=np.float64) for p in edges]
    for _ in range(n):
        shaken = [p + rng.normal(0, edge_px, 2) for p in base]
        kf = 1 + rng.normal(0, f_rel)
        kd = 1 + rng.normal(0, d_rel)
        try:
            out.append(float(measure_fn(shaken, kf, kd)))
        except (ValueError, ArithmeticError, np.linalg.LinAlgError):
            continue
    if len(out) < max(10, n // 5):
        raise ValueError("Monte Carlo gagal: terlalu banyak putaran tidak terhitung.")
    arr = np.array(out)
    return (
        float(np.median(arr)),
        float(np.percentile(arr, 2.5)),
        float(np.percentile(arr, 97.5)),
        len(out),
    )


def status(cam_ok: bool, cal2_ok: bool, cal3_ok: bool, d_type: str, n_st: int) -> str:
    """Empat tingkat status hasil."""
    if not cam_ok:
        return "ESTIMASI"
    if cal2_ok and cal3_ok and d_type == "pi-tape" and n_st >= 5:
        return "VALID"
    if cal3_ok:
        return "VALID-TERBATAS"
    return "ESTIMASI"
