"""Adegan sintetis: silinder 3D dengan jawaban yang diketahui, diproyeksikan ke gambar."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from deepinsight_engine.pipecal.camera import PipeCamera

RADIUS = 20.45


@dataclass
class Scene:
    cam: PipeCamera
    c0: np.ndarray
    d: np.ndarray
    radius: float
    normals: list[np.ndarray]

    def silhouette(self, t_values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        sides = []
        for n in self.normals:
            pts = np.array([self.c0 + t * self.d + self.radius * n for t in t_values])
            sides.append(self.cam.project(pts))
        if sides[0][:, 1].mean() <= sides[1][:, 1].mean():
            return sides[0], sides[1]
        return sides[1], sides[0]

    def surface(self, t: float, phi: float, e1: np.ndarray, e2: np.ndarray) -> np.ndarray:
        radial = np.cos(phi) * e1 + np.sin(phi) * e2
        return self.c0 + t * self.d + self.radius * radial


def make_camera(dist: tuple[float, ...] = (-0.12, 0.03, 0.0005, -0.0004, 0.0)) -> PipeCamera:
    k = np.array([[1050.0, 0.0, 640.0], [0.0, 1050.0, 360.0], [0.0, 0.0, 1.0]])
    return PipeCamera(k, np.array(dist), (1280, 720))


def make_scene(
    psi_deg: float = 34.0,
    start: tuple[float, float, float] = (-60.0, 0.0, 150.0),
    cam: PipeCamera | None = None,
) -> Scene:
    camera = cam or make_camera()
    psi = np.radians(psi_deg)
    d = np.array([np.cos(psi), 0.0, np.sin(psi)])
    c0 = np.array(start)
    e1 = np.cross(d, [0.0, 1.0, 0.0])
    e1 = e1 / np.linalg.norm(e1)
    e2 = np.cross(d, e1)
    wp = np.array([c0 @ e1, c0 @ e2])
    base = np.arctan2(wp[1], wp[0]) + np.pi
    spread = np.arccos(RADIUS / np.linalg.norm(wp))
    normals = [np.cos(a) * e1 + np.sin(a) * e2 for a in (base + spread, base - spread)]
    return Scene(camera, c0, d, RADIUS, normals)


def noisy_clicks(
    scene: Scene, count: int = 7, noise_px: float = 0.0, seed: int = 1
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    top, bot = scene.silhouette(np.linspace(0.0, 200.0, count))
    return top + rng.normal(0, noise_px, top.shape), bot + rng.normal(0, noise_px, bot.shape)
