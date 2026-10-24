import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent))
from pipecal_scene import RADIUS, make_scene, noisy_clicks  # noqa: E402

from deepinsight_engine.pipecal import angles, cal1, uncertainty  # noqa: E402
from deepinsight_engine.pipecal.cal3 import (  # noqa: E402
    auto_stations,
    axis_model,
    clip_range,
    silhouettes,
)
from deepinsight_engine.pipecal.cal4 import fit_ab  # noqa: E402
from deepinsight_engine.pipecal.measure import (  # noqa: E402
    axis_param,
    clock,
    length_along_axis,
)


def test_axis_param_exact() -> None:
    c, d = np.array([1.0, 2.0, 3.0]), np.array([0.0, 0.0, 1.0])
    r = np.array([1.0, 2.0, 1.0]) + np.array([0.0, 0.0, 0.0])
    r = np.array([0.0, 0.0, 1.0]) + np.array([1.0, 0.0, 0.0])
    t = axis_param(r, c, d)
    p = c + t * d
    s = (p @ r) / (r @ r)
    assert np.linalg.norm(p - s * r) == pytest.approx(
        min(
            np.linalg.norm(c + u * d - (((c + u * d) @ r) / (r @ r)) * r)
            for u in np.linspace(-20, 20, 4001)
        ),
        abs=1e-2,
    )


@pytest.mark.parametrize("psi", [10, 34, 50])
@pytest.mark.parametrize("noise", [0.0, 1.0])
def test_chain(psi: int, noise: float) -> None:
    sc = make_scene(psi)
    top, bot = noisy_clicks(sc, 7, noise)
    sil = silhouettes(sc.cam, top, bot)
    rng = clip_range(sil.l_top, 1280, 720)
    pairs = auto_stations(sil.l_top, sil.l_bot, sil.vp, (rng[0] + 30, rng[1] - 30), 100)
    m = axis_model(sc.cam, sil, pairs, RADIUS)
    assert np.degrees(np.arccos(abs(m.d @ sc.d))) < 0.8
    assert m.passed
    p1 = sc.cam.project((sc.c0 + 20 * sc.d)[None])[0]
    p2 = sc.cam.project((sc.c0 + 180 * sc.d)[None])[0]
    assert abs(length_along_axis(sc.cam, p1, p2, m.c, m.d) / 160 - 1) < 0.025


def test_fit_ab_recovers() -> None:
    rng = np.random.default_rng(1)
    m = rng.uniform(0.2, 1.0, 80)
    z = 1.0 / (0.7 * m + 0.1)
    z[:6] *= 3
    a, b, _ = fit_ab(m, z, "disparity")
    assert a == pytest.approx(0.7, rel=0.05)
    assert b == pytest.approx(0.1, abs=0.03)


def test_status_tiers() -> None:
    assert uncertainty.status(True, True, True, "pi-tape", 5) == "VALID"
    assert uncertainty.status(True, True, True, "baja", 5) == "VALID-TERBATAS"
    assert uncertainty.status(True, True, False, "pi-tape", 5) == "ESTIMASI"
    assert uncertainty.status(False, True, True, "pi-tape", 5) == "ESTIMASI"


def test_coverage_and_clock_and_angles() -> None:
    grid, ok = cal1.coverage([np.array([[10.0, 10.0]])], 300, 300, n_min=1)
    assert grid[0] == 1 and not ok
    assert clock(0.0) == 12
    assert angles.angle_a((0, 0), (1, 0)) == pytest.approx(0.0, abs=1e-9)
