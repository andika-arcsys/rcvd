"""Geometri bidang: jarak, shoelace, Heron, dan perpotongan sisi."""

from __future__ import annotations

import math
from collections.abc import Sequence

from .types import Point


def distance(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def shoelace(points: Sequence[Point]) -> float:
    acc = 0.0
    count = len(points)
    for index in range(count):
        x1, y1 = points[index]
        x2, y2 = points[(index + 1) % count]
        acc += x1 * y2 - x2 * y1
    return acc * 0.5


def heron(side_a: float, side_b: float, side_c: float) -> float:
    semi = (side_a + side_b + side_c) * 0.5
    product = semi * (semi - side_a) * (semi - side_b) * (semi - side_c)
    return math.sqrt(max(0.0, product))


def side_lengths(points: Sequence[Point], scale: float) -> tuple[float, ...]:
    count = len(points)
    return tuple(
        distance(points[index], points[(index + 1) % count]) * scale for index in range(count)
    )


def diagonal_lengths(points: Sequence[Point], scale: float) -> tuple[float, float]:
    return (
        distance(points[0], points[2]) * scale,
        distance(points[1], points[3]) * scale,
    )


def _orient(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _proper_cross(a: Point, b: Point, c: Point, d: Point) -> bool:
    left = _orient(a, b, c) * _orient(a, b, d)
    right = _orient(c, d, a) * _orient(c, d, b)
    return left < 0.0 and right < 0.0


def _adjacent(i: int, j: int, count: int) -> bool:
    return (i + 1) % count == j or (j + 1) % count == i


def self_intersects(points: Sequence[Point]) -> bool:
    count = len(points)
    for i in range(count):
        start = points[i]
        end = points[(i + 1) % count]
        for j in range(i + 1, count):
            if _adjacent(i, j, count):
                continue
            other_start = points[j]
            other_end = points[(j + 1) % count]
            if _proper_cross(start, end, other_start, other_end):
                return True
    return False
