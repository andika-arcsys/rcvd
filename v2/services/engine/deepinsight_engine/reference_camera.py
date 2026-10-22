"""Profil generik sebelum foto K1. Semua angka dibaca dari config."""

from __future__ import annotations

from .core.camera_file import CameraFile
from .core.config import Settings
from .spatial.geometry import default_intrinsics

# 1 cm = 10 mm. Satuan, bukan ukuran marker.
_MM_PER_CM = 10.0


def reference_camera(settings: Settings) -> CameraFile:
    """Pinhole pada resolusi video. Kotak dan distorsi dari camera.reference.

    Sisi marker mengikuti laser.ref_cm. RMS, tanggal, port, dan air tetap kosong.
    """
    video = settings.thresholds.video
    prior = settings.thresholds.camera.reference
    intrinsics = default_intrinsics(video.width, video.height, None)
    return CameraFile(
        schema_version=1,
        id=prior.id,
        square_mm=prior.square_mm,
        image_width=video.width,
        image_height=video.height,
        corners_cols=prior.corners_cols,
        corners_rows=prior.corners_rows,
        camera_matrix=[
            intrinsics.fx,
            0.0,
            intrinsics.cx,
            0.0,
            intrinsics.fy,
            intrinsics.cy,
            0.0,
            0.0,
            1.0,
        ],
        dist_coeffs=[float(item) for item in prior.dist_coeffs],
        board=prior.board,
        marker_mm=_marker_mm(settings.thresholds.laser.ref_cm),
        dictionary=prior.dictionary,
        origin="reference",
    )


def _marker_mm(ref_cm: float | None) -> float | None:
    if ref_cm is None or ref_cm <= 0:
        return None
    return float(ref_cm) * _MM_PER_CM
