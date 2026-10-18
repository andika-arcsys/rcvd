"""Kalibrasi papan catur. Ambang RMS hanya dari config, tidak dari kode."""

from __future__ import annotations

import importlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .core.camera_file import CameraFile, rms_decision
from .core.config import load_settings
from .core.errors import EngineError


def calibrate_folder(
    config_dir: Path,
    folder: Path,
    camera_id: str,
    square_mm: float,
    corners_cols: int,
    corners_rows: int,
) -> tuple[int, str]:
    if camera_id.startswith("_") or not camera_id.strip():
        return 2, "ID kamera tidak boleh kosong atau diawali garis bawah."
    if square_mm <= 0 or corners_cols < 3 or corners_rows < 3:
        return 2, "Ukuran kotak dan jumlah sudut harus positif. Sudut minimal 3×3."
    images = _images(folder)
    if not images:
        return 2, f"Tidak ada foto di {folder}."
    try:
        settings = load_settings(config_dir)
    except EngineError as exc:
        return 2, exc.spec.message_id
    camera = settings.thresholds.camera
    found = _calibrate(images, square_mm, corners_cols, corners_rows)
    if isinstance(found, str):
        return 2, found
    rms, matrix, dist, width, height = found
    band = rms_decision(rms, camera.rms_good_px, camera.rms_max_px)
    if band == "reject":
        return 1, (f"RMS {rms:.6f} melewati ambang {camera.rms_max_px}. Berkas tidak ditulis.")
    _write(
        config_dir,
        camera_id,
        square_mm,
        corners_cols,
        corners_rows,
        width,
        height,
        matrix,
        dist,
        rms,
        band == "warn",
    )
    if band == "warn":
        return 0, (
            f"Kalibrasi {camera_id} ditulis dengan peringatan. "
            f"RMS {rms:.6f} di atas {camera.rms_good_px} dan tidak di atas {camera.rms_max_px}."
        )
    return 0, f"Kalibrasi {camera_id} ditulis. RMS {rms:.6f}."


def _images(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    names = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
    return sorted(path for path in folder.iterdir() if path.suffix.lower() in names)


def _calibrate(
    images: list[Path], square_mm: float, cols: int, rows: int
) -> str | tuple[float, list[float], list[float], int, int]:
    try:
        cv2: Any = importlib.import_module("cv2")
        import numpy as np
    except ImportError:
        return "OpenCV tidak terpasang."
    object_point = _object_points(np, cols, rows, square_mm)
    objects: list[object] = []
    corners: list[object] = []
    width = height = 0
    for path in images:
        gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            continue
        height, width = gray.shape[:2]
        ok, found = cv2.findChessboardCorners(gray, (cols, rows), None)
        if not ok:
            continue
        objects.append(object_point)
        corners.append(found)
    if len(corners) < 3:
        return "Papan catur terbaca pada kurang dari 3 foto."
    rms, matrix, dist, _rvecs, _tvecs = cv2.calibrateCamera(
        objects, corners, (width, height), None, None
    )
    flat_matrix = [float(v) for v in matrix.reshape(-1)]
    flat_dist = [float(v) for v in dist.reshape(-1)]
    return float(rms), flat_matrix, flat_dist, width, height


def _object_points(np: object, cols: int, rows: int, square_mm: float) -> object:
    import numpy as real_np

    del np
    grid = real_np.zeros((cols * rows, 3), real_np.float32)
    grid[:, :2] = real_np.mgrid[0:cols, 0:rows].T.reshape(-1, 2)
    return grid * float(square_mm)


def _write(
    config_dir: Path,
    camera_id: str,
    square_mm: float,
    cols: int,
    rows: int,
    width: int,
    height: int,
    matrix: list[float],
    dist: list[float],
    rms: float,
    warn: bool,
) -> None:
    payload = CameraFile(
        schema_version=1,
        id=camera_id,
        square_mm=square_mm,
        image_width=width,
        image_height=height,
        corners_cols=cols,
        corners_rows=rows,
        camera_matrix=matrix,
        dist_coeffs=dist,
        rms=rms,
        calibrated_at=datetime.now(UTC).date().isoformat(),
    )
    target = config_dir / "cameras" / f"{camera_id}.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(payload.model_dump(), sort_keys=False, allow_unicode=True)
    if warn:
        note = "# RMS pada pita peringatan: di atas rms_good_px, tidak di atas rms_max_px.\n"
        body = note + body
    target.write_text(body, encoding="utf-8")
