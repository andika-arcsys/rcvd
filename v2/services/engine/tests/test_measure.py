"""Vektor emas measure_cases.json: Python harus sama dengan berkas ini."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

import cv2
import numpy as np
import pytest

from deepinsight_engine.core.config import load_settings
from deepinsight_engine.core.errors import EngineError
from deepinsight_engine.measure import (
    Camera,
    SegmentIn,
    area,
    calibrate,
    calibration_status,
    critical_limit,
    freeze_pair,
    heron_cross_check,
    length,
    limits_from_thresholds,
    rod_test,
    span,
    span_warning,
    tape_check,
    undistort_point,
)
from deepinsight_engine.measure.types import MeasureLimits, Point

GOLDEN = Path(__file__).resolve().parents[3] / "tests" / "golden" / "measure_cases.json"
PHASE0 = Path(__file__).resolve().parents[3] / "tests" / "golden" / "measure_vectors.json"
REPO_CONFIG = Path(__file__).resolve().parents[3] / "config"


def _load() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(GOLDEN.read_text(encoding="utf-8")))


def _point(raw: list[float]) -> Point:
    return (float(raw[0]), float(raw[1]))


def _camera(raw: dict[str, Any] | None) -> Camera | None:
    if raw is None:
        return None
    k1, k2, p1, p2, k3 = (float(item) for item in cast(list[float], raw["dist"]))
    return Camera(
        fx=float(raw["fx"]),
        fy=float(raw["fy"]),
        cx=float(raw["cx"]),
        cy=float(raw["cy"]),
        k1=k1,
        k2=k2,
        p1=p1,
        p2=p2,
        k3=k3,
    )


def _limits(data: dict[str, Any]) -> MeasureLimits:
    return MeasureLimits(**cast(dict[str, Any], data["limits"]))


def _calibration(raw: dict[str, Any], limits: MeasureLimits) -> Any:
    return calibrate(
        _point(cast(list[float], raw["p1"])),
        _point(cast(list[float], raw["p2"])),
        float(raw["ref_m"]),
        float(raw["click_sigma_px"]),
        limits,
        _camera(cast(dict[str, Any] | None, raw["camera"])),
    )


def _segments(raw: list[dict[str, Any]]) -> tuple[SegmentIn, ...]:
    return tuple(
        SegmentIn(
            id=str(item["id"]),
            pairs=tuple(
                (float(pair[0]), float(pair[1])) for pair in cast(list[list[float]], item["pairs"])
            ),
        )
        for item in raw
    )


def _run(case: dict[str, Any], limits: MeasureLimits) -> dict[str, Any]:
    op = str(case["op"])
    if op == "calibrate":
        return asdict(_calibration(case, limits))
    if op == "status":
        status = calibration_status(float(case["rel_uncert"]), bool(case["camera_present"]), limits)
        return {"status": status}
    if op == "length":
        cal = _calibration(cast(dict[str, Any], case["calibration"]), limits)
        payload = asdict(
            length(
                _point(cast(list[float], case["p1"])),
                _point(cast(list[float], case["p2"])),
                cal,
                limits,
            )
        )
        payload["scale_m_per_px"] = cal.scale_m_per_px
        payload["status"] = cal.status
        payload["nodes"] = cal.nodes
        return payload
    if op == "area":
        cal = _calibration(cast(dict[str, Any], case["calibration"]), limits)
        points = tuple(
            _point(cast(list[float], item)) for item in cast(list[list[float]], case["points"])
        )
        return asdict(area(points, cal, limits))
    if op == "heron_cross_check":
        heron_cross_check(float(case["a"]), float(case["b"]), limits)
        return {"ok": True}
    if op == "rod_test":
        return asdict(rod_test(float(case["measured_m"]), limits))
    if op == "freeze_pair":
        return asdict(freeze_pair(float(case["a_m"]), float(case["b_m"]), limits))
    if op == "tape_check":
        return asdict(tape_check(float(case["length_total_m"]), float(case["tape_m"]), limits))
    if op == "critical_limit":
        return {"critical_limit_m": critical_limit(str(case["diameter"]), limits)}
    if op == "span_warning":
        return {"warning": span_warning(float(case["length_m"]), str(case["diameter"]), limits)}
    if op == "span":
        return asdict(
            span(
                _segments(cast(list[dict[str, Any]], case["segments"])),
                str(case["g_left"]),
                str(case["g_right"]),
                str(case["diameter"]),
                limits,
            )
        )
    raise AssertionError(op)


def _close(actual: object, expected: object, tol: float, path: str) -> None:
    if isinstance(expected, bool):
        assert actual is expected, path
        return
    if isinstance(expected, int | float):
        assert isinstance(actual, int | float), path
        limit = tol * max(1.0, abs(float(expected)))
        assert abs(float(actual) - float(expected)) <= limit, path
        return
    if isinstance(expected, str):
        assert actual == expected, path
        return
    if expected is None:
        assert actual is None, path
        return
    if isinstance(expected, list):
        assert isinstance(actual, list | tuple), path
        assert len(actual) == len(expected), path
        for index, item in enumerate(expected):
            _close(actual[index], item, tol, f"{path}[{index}]")
        return
    if isinstance(expected, dict):
        assert isinstance(actual, dict), path
        for key, item in expected.items():
            assert key in actual, f"{path}.{key}"
            _close(actual[key], item, tol, f"{path}.{key}")
        return
    raise AssertionError(path)


def test_golden_limits_match_config() -> None:
    data = _load()
    got = asdict(limits_from_thresholds(load_settings(REPO_CONFIG).thresholds))
    assert got == data["limits"]


def test_golden_cases_match_python() -> None:
    data = _load()
    limits = _limits(data)
    tol = float(data["tolerance_rel"])
    sigma = load_settings(REPO_CONFIG).thresholds.calibration.click_sigma_px
    for case in cast(list[dict[str, Any]], data["cases"]):
        name = str(case["name"])
        if "click_sigma_px" in case:
            assert case["click_sigma_px"] == sigma, name
        nested = case.get("calibration")
        if isinstance(nested, dict):
            assert nested["click_sigma_px"] == sigma, name
        if "error" in case:
            with pytest.raises(EngineError) as info:
                _run(case, limits)
            assert info.value.spec.code == case["error"], name
            assert info.value.spec.message_id == case["message"], name
            continue
        _close(_run(case, limits), case["expect"], tol, name)


def test_undistort_matches_opencv_and_phase0() -> None:
    data = _load()
    limits = _limits(data)
    published = next(
        item
        for item in cast(list[dict[str, Any]], json.loads(PHASE0.read_text(encoding="utf-8")))
        if item["name"] == "undistort_node_opencv_pinhole"
    )
    camera_raw = cast(dict[str, Any], published["camera"])
    camera = _camera(
        {
            "fx": camera_raw["fx"],
            "fy": camera_raw["fy"],
            "cx": camera_raw["cx"],
            "cy": camera_raw["cy"],
            "dist": camera_raw["dist"],
        }
    )
    assert camera is not None
    matrix = np.array(
        [[camera.fx, 0.0, camera.cx], [0.0, camera.fy, camera.cy], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    dist = np.array([camera.k1, camera.k2, camera.p1, camera.p2, camera.k3], dtype=np.float64)
    raw_points = [
        cast(list[float], published["node1"]),
        cast(list[float], published["node2"]),
        cast(list[float], published["a"]),
        cast(list[float], published["b"]),
    ]
    src = np.array(raw_points, dtype=np.float64).reshape(-1, 1, 2)
    criteria = (cv2.TERM_CRITERIA_COUNT, limits.undistort_iterations, 0.0)
    opencv = cv2.undistortPoints(src, matrix, dist, P=matrix, criteria=criteria).reshape(-1, 2)
    for raw, row in zip(raw_points, opencv, strict=True):
        got = undistort_point(_point(raw), camera, limits.undistort_iterations)
        assert abs(got[0] - float(row[0])) <= 1e-12
        assert abs(got[1] - float(row[1])) <= 1e-12
    stored = cast(dict[str, list[float]], published["undistorted"])
    for key, raw in (
        ("node1", raw_points[0]),
        ("node2", raw_points[1]),
        ("a", raw_points[2]),
        ("b", raw_points[3]),
    ):
        got = undistort_point(_point(raw), camera, limits.undistort_iterations)
        expect = stored[key]
        assert abs(got[0] - float(expect[0])) <= 1e-9
        assert abs(got[1] - float(expect[1])) <= 1e-9
