"""Undistort titik model pinhole OpenCV. Gambar bukti tidak diubah."""

from __future__ import annotations

from .types import Camera, Point


def undistort_point(point: Point, camera: Camera, iterations: int) -> Point:
    """Iterasi balik distorsi radial-tangensial (k1, k2, p1, p2, k3)."""
    u, v = point
    x0 = (u - camera.cx) / camera.fx
    y0 = (v - camera.cy) / camera.fy
    x, y = x0, y0
    for _ in range(iterations):
        r2 = x * x + y * y
        icdist = 1.0 / (1.0 + ((camera.k3 * r2 + camera.k2) * r2 + camera.k1) * r2)
        delta_x = 2.0 * camera.p1 * x * y + camera.p2 * (r2 + 2.0 * x * x)
        delta_y = camera.p1 * (r2 + 2.0 * y * y) + 2.0 * camera.p2 * x * y
        x = (x0 - delta_x) * icdist
        y = (y0 - delta_y) * icdist
    return (x * camera.fx + camera.cx, y * camera.fy + camera.cy)


def map_point(point: Point, camera: Camera | None, iterations: int) -> Point:
    if camera is None:
        return point
    return undistort_point(point, camera, iterations)
