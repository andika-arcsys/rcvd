"""Model kamera pinhole dengan distorsi Brown-Conrady. Rumus (A1.1), (A1.4) sampai (A1.7)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from ..core.camera_file import CameraFile
from ..spatial.da3_frame import camera_k


class FrameMismatchError(ValueError):
    """Resolusi frame tidak sama dengan camera file."""


@dataclass(frozen=True)
class PipeCamera:
    K: np.ndarray
    dist: np.ndarray
    size: tuple[int, int]
    approximate: bool = False

    @classmethod
    def from_file(cls, camera: CameraFile, width: int, height: int) -> PipeCamera:
        matrix = camera.camera_matrix
        if matrix is None or camera.image_width is None or camera.image_height is None:
            raise FrameMismatchError("Berkas kamera belum punya matriks dan resolusi.")
        dist = np.array(camera.dist_coeffs or [0.0] * 5, dtype=np.float64)
        same = (camera.image_width, camera.image_height) == (width, height)
        if same:
            return cls(np.array(matrix, dtype=np.float64).reshape(3, 3), dist, (width, height))
        if camera.origin != "reference":
            raise FrameMismatchError(
                f"Resolusi frame {width}×{height} tidak sama dengan camera file "
                f"{camera.image_width}×{camera.image_height}. Kalibrasi ulang di resolusi inspeksi."
            )
        fx, fy, cx, cy = camera_k(matrix, width, height, camera.image_width, camera.image_height)
        scaled = np.array([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], dtype=np.float64)
        return cls(scaled, dist, (width, height), approximate=True)

    def check(self, frame_w: int, frame_h: int) -> bool:
        return (frame_w, frame_h) == self.size

    def undistort(self, pts: Any) -> np.ndarray:
        """Koordinat ternormalisasi bebas distorsi."""
        flat = np.asarray(pts, dtype=np.float64).reshape(-1, 1, 2)
        return np.asarray(cv2.undistortPoints(flat, self.K, self.dist)).reshape(-1, 2)

    def undistort_px(self, pts: Any) -> np.ndarray:
        """Titik bebas distorsi dalam piksel (P = K). Garis siluet difit di ruang ini."""
        flat = np.asarray(pts, dtype=np.float64).reshape(-1, 1, 2)
        return np.asarray(cv2.undistortPoints(flat, self.K, self.dist, P=self.K)).reshape(-1, 2)

    def rays(self, pts: Any) -> np.ndarray:
        # Rumus (A1.5)
        return self.rays_ud(self.undistort_px(pts))

    def rays_ud(self, pts_ud: Any) -> np.ndarray:
        """Sinar satuan dari titik yang sudah bebas distorsi (piksel)."""
        p = np.asarray(pts_ud, dtype=np.float64).reshape(-1, 2)
        fx, fy, cx, cy = self.K[0, 0], self.K[1, 1], self.K[0, 2], self.K[1, 2]
        r = np.column_stack([(p[:, 0] - cx) / fx, (p[:, 1] - cy) / fy, np.ones(len(p))])
        return np.asarray(r / np.linalg.norm(r, axis=1, keepdims=True))

    def project(self, points: Any) -> np.ndarray:
        # Rumus (A1.4) dengan distorsi (A1.6) dan (A1.7)
        pts = np.asarray(points, dtype=np.float64).reshape(-1, 3)
        zero = np.zeros(3)
        uv, _ = cv2.projectPoints(pts, zero, zero, self.K, self.dist)
        return np.asarray(uv).reshape(-1, 2)

    def to_raw_px(self, pts_ud: Any) -> np.ndarray:
        """Titik bebas distorsi (piksel) kembali ke piksel frame asli untuk digambar."""
        rays = self.rays_ud(pts_ud)
        return self.project(rays / rays[:, 2:3])

    def scaled(self, factor: float) -> PipeCamera:
        k = self.K.copy()
        k[0, 0] *= factor
        k[1, 1] *= factor
        return PipeCamera(k, self.dist, self.size, self.approximate)


def screen_to_frame(sx: float, sy: float, ox: float, oy: float, zoom: float) -> tuple[float, float]:
    # Rumus (A1.1)
    return (sx - ox) / zoom, (sy - oy) / zoom
