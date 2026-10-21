"""Conf, pita galat, lebar siluet, dan panjang 3D. Tanpa GPU."""

from __future__ import annotations

import numpy as np
import pytest

from deepinsight_engine.spatial.band import scored_depth
from deepinsight_engine.spatial.estimate import estimate_scene
from deepinsight_engine.spatial.geometry import CameraIntrinsics, read_window

_FRONT = 0.2096291201783626
_FAR_FRONT = 0.722466


def test_gradient_score_holds_calibration_depth_and_opens_the_ratio() -> None:
    assert scored_depth(1.4, 0.0) == pytest.approx(1.4)
    assert scored_depth(2.0, 2.0) == pytest.approx(2.0)
    farther = scored_depth(4.0, 2.0)
    nearer = scored_depth(1.0, 2.0)
    assert farther == pytest.approx(2.0 * (2.0**1.5))
    assert nearer < 1.0
    assert nearer / 2.0 == pytest.approx((0.5) ** 1.5)


def test_low_confidence_pixels_leave_the_median() -> None:
    depth = np.full((21, 21), 8.0, dtype=np.float32)
    conf = np.full((21, 21), 0.1, dtype=np.float32)
    depth[7:11, 7:11] = 2.0
    conf[7:11, 7:11] = 1.0
    kept = read_window(depth, (10, 10), conf=conf, conf_min=0.5)
    assert kept.depth == pytest.approx(2.0)
    mixed = read_window(depth, (10, 10), conf=conf, conf_min=0.0)
    assert mixed.depth == pytest.approx(8.0)


def test_sparse_window_is_marked_uncertain() -> None:
    depth = np.full((21, 21), 3.0, dtype=np.float32)
    conf = np.zeros((21, 21), dtype=np.float32)
    conf[10, 6:10] = 1.0
    sample = read_window(depth, (9, 10), conf=conf, conf_min=0.5)
    assert sample.count < 10
    assert sample.uncertain is True
    scene = estimate_scene(
        depth,
        40.0,
        "frm",
        ((2.0, 10.0), (12.0, 10.0)),
        0.2,
        [((4.0, 10.0), (14.0, 10.0))],
        [],
        [],
        conf=conf,
        conf_min=0.5,
    )
    row = scene["lengths"]
    assert isinstance(row, list)
    assert row[0]["uncertain_depth"] is True
    warnings = scene["warnings"]
    assert isinstance(warnings, list)
    assert "kedalaman tidak yakin" in warnings


def test_uncertainty_keeps_a_five_percent_floor() -> None:
    depth = np.full((80, 500), 2.0, dtype=np.float32)
    scene = estimate_scene(
        depth,
        100.0,
        "frm",
        ((10.0, 40.0), (410.0, 40.0)),
        0.4,
        [((10.0, 40.0), (410.0, 40.0))],
        [],
        [],
        click_sigma_px=1.5,
    )
    lengths = scene["lengths"]
    assert isinstance(lengths, list)
    distance = float(lengths[0]["distance_cm"])
    band = float(lengths[0]["uncertainty_cm"])
    assert band == pytest.approx(distance * 0.05)
    warnings = scene["warnings"]
    assert isinstance(warnings, list)
    assert any("Rasio gradasi 1.50" in item for item in warnings)
    short = estimate_scene(
        np.full((40, 80), 2.0, dtype=np.float32),
        100.0,
        "frm",
        ((10.0, 20.0), (20.0, 20.0)),
        0.4,
        [((10.0, 20.0), (30.0, 20.0))],
        [],
        [],
        click_sigma_px=1.5,
    )
    row = short["lengths"]
    assert isinstance(row, list)
    short_distance = float(row[0]["distance_cm"])
    short_band = float(row[0]["uncertainty_cm"])
    assert short_band > short_distance * 0.05
    assert short_band > short_distance * 0.20


def test_facing_width_recovers_the_far_diameter_when_focal_is_real() -> None:
    depth = np.full((160, 220), _FRONT, dtype=np.float32)
    depth[37:44, 103:110] = _FAR_FRONT
    facing = _scene(depth, kinds=["facing"], intrinsics=_water(), source="camera_file")
    plain = _scene(depth, kinds=["span"], intrinsics=_water(), source="camera_file")
    got = facing["lengths"]
    other = plain["lengths"]
    assert isinstance(got, list) and isinstance(other, list)
    assert got[0]["distance_cm"] == pytest.approx(10.0, rel=0.01)
    assert got[0]["kind"] == "facing"
    assert other[0]["distance_cm"] != pytest.approx(float(got[0]["distance_cm"]), rel=0.02)


def test_facing_without_a_real_focal_stays_on_the_midpoint_span() -> None:
    depth = np.full((40, 80), 2.0, dtype=np.float32)
    depth[17:24, 17:24] = 4.0
    scene = estimate_scene(
        depth,
        None,
        "frm",
        ((10.0, 10.0), (20.0, 10.0)),
        0.4,
        [((10.0, 20.0), (30.0, 20.0))],
        [],
        [],
        length_kinds=["facing"],
    )
    lengths = scene["lengths"]
    assert isinstance(lengths, list)
    assert lengths[0]["distance_cm"] == pytest.approx(160.0 * scored_depth(4.0, 2.0) / 4.0)
    assert scene["intrinsics_source"] == "longest_side"
    assert scene["focal_px"] is None
    warnings = scene["warnings"]
    assert isinstance(warnings, list)
    assert any("sisi terpanjang" in item for item in warnings)


def test_length3d_keeps_the_axial_gap() -> None:
    depth = np.full((40, 80), 2.0, dtype=np.float32)
    depth[17:24, 25:32] = 6.0
    scene = estimate_scene(
        depth,
        None,
        "frm",
        ((10.0, 10.0), (20.0, 10.0)),
        0.4,
        [((10.0, 20.0), (30.0, 20.0))],
        [],
        [],
        intrinsics=CameraIntrinsics(100, 100, 40, 20),
        intrinsics_source="prediction.intrinsics",
        length_kinds=["length3d"],
        model_id="depth-anything/DA3METRIC-LARGE",
        process_res=504,
        resize_method="upper_bound_resize",
        conf_min=0.0,
    )
    lengths = scene["lengths"]
    assert isinstance(lengths, list)
    scale = 2.0
    z_a = scored_depth(2.0, 2.0) * scale
    z_b = scored_depth(6.0, 2.0) * scale
    x_a = (10.0 - 40.0) * z_a / 100.0
    x_b = (30.0 - 40.0) * z_b / 100.0
    gap_cm = ((x_a - x_b) ** 2 + (z_a - z_b) ** 2) ** 0.5 * 100.0
    assert lengths[0]["distance_cm"] == pytest.approx(gap_cm)
    assert lengths[0]["sample_u"] == pytest.approx(12.0)
    assert lengths[0]["sample_u_b"] == pytest.approx(28.0)
    assert scene["model_id"] == "depth-anything/DA3METRIC-LARGE"
    assert scene["process_res"] == 504
    assert scene["conf_min"] == 0.0
    assert scene["intrinsics_source"] == "prediction.intrinsics"


def _water() -> CameraIntrinsics:
    return CameraIntrinsics(100.0, 100.0, 110.0, 80.0, calibrated_underwater=True)


def _scene(
    depth: np.ndarray,
    *,
    kinds: list[str],
    intrinsics: CameraIntrinsics | None = None,
    source: str | None = None,
    conf: np.ndarray | None = None,
    conf_min: float = 0.0,
) -> dict[str, object]:
    return estimate_scene(
        depth,
        None,
        "frm",
        ((80.0, 100.0), (120.0, 100.0)),
        0.10,
        [((100.0, 40.0), (113.0, 40.0))],
        [],
        [],
        intrinsics=intrinsics,
        intrinsics_source=source,
        length_kinds=kinds,
        conf=conf,
        conf_min=conf_min,
        click_sigma_px=1.5,
    )
