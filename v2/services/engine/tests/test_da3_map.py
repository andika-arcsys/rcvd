"""Pemetaan piksel PNG ke peta process_res, tanpa GPU."""

from __future__ import annotations

import numpy as np
import pytest

from deepinsight_engine.spatial.da3_frame import (
    align_map,
    map_png_to_proc,
    map_proc_to_png,
    process_geometry,
    scale_prediction_k,
)


def test_upper_bound_resize_matches_the_official_sizes() -> None:
    wide = process_geometry(1920, 1080, 504)
    assert (wide.bound_w, wide.bound_h, wide.proc_w, wide.proc_h) == (504, 284, 504, 280)
    assert (wide.crop_x, wide.crop_y) == (0, 0)
    square = process_geometry(504, 504, 504)
    assert (square.proc_w, square.proc_h, square.crop_x, square.crop_y) == (504, 504, 0, 0)


def test_upper_bound_crop_records_the_center_offset() -> None:
    geom = process_geometry(504, 376, 504, "upper_bound_crop")
    assert (geom.bound_w, geom.bound_h) == (504, 376)
    assert (geom.proc_w, geom.proc_h) == (504, 364)
    assert (geom.crop_x, geom.crop_y) == (0, 6)


def test_identity_map_reads_png_x_at_corners_and_center() -> None:
    geom = process_geometry(504, 504, 504)
    depth = np.tile(np.arange(504, dtype=np.float32), (504, 1))
    aligned = align_map(depth, geom, nearest=False)
    for u, v in ((0, 0), (252, 252), (503, 503)):
        assert aligned[v, u] == pytest.approx(u)
        back = map_proc_to_png(*map_png_to_proc(u, v, geom), geom)
        assert back == pytest.approx((u, v))


def test_resized_corners_and_center_sample_the_same_map_location() -> None:
    geom = process_geometry(1920, 1080, 504)
    depth = np.tile(np.arange(geom.proc_w, dtype=np.float32), (geom.proc_h, 1))
    aligned = align_map(depth, geom, nearest=False)
    for u, v in ((0, 0), (960, 540), (1919, 1079)):
        map_u, map_v = map_png_to_proc(u, v, geom)
        back_u, back_v = map_proc_to_png(map_u, map_v, geom)
        assert (back_u, back_v) == pytest.approx((u, v))
        assert aligned[v, u] == pytest.approx(_bilinear(depth, map_u, map_v))


def test_prediction_intrinsics_scale_to_the_png() -> None:
    geom = process_geometry(1920, 1080, 504)
    matrix = np.array([[400.0, 0.0, 252.0], [0.0, 220.0, 140.0], [0.0, 0.0, 1.0]])
    fx, fy, cx, cy = scale_prediction_k(matrix, geom)
    assert fx == pytest.approx(400.0 * 1920 / 504)
    assert fy == pytest.approx(220.0 * 1080 / 280)
    assert cx == pytest.approx(252.0 * 1920 / 504)
    assert cy == pytest.approx(140.0 * 1080 / 280)


def _bilinear(grid: np.ndarray, x: float, y: float) -> float:
    height, width = grid.shape
    x = float(np.clip(x, 0, width - 1))
    y = float(np.clip(y, 0, height - 1))
    x0, y0 = int(np.floor(x)), int(np.floor(y))
    x1, y1 = min(x0 + 1, width - 1), min(y0 + 1, height - 1)
    wx, wy = x - x0, y - y0
    return float(
        grid[y0, x0] * (1 - wx) * (1 - wy)
        + grid[y0, x1] * wx * (1 - wy)
        + grid[y1, x0] * (1 - wx) * wy
        + grid[y1, x1] * wx * wy
    )
