"""Kalibrasi papan catur OpenCV.

Langkah mengikuti tutorial VisionBrick: cari sudut dalam, haluskan dengan
cornerSubPix (jendela 11×11, 30 iterasi), lalu calibrateCamera. Ambang RMS
hanya dari config, tidak dari kode. Titik objek dalam milimeter.
"""

from __future__ import annotations

import importlib
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .core.camera_file import CameraFile, rms_decision
from .core.config import load_settings
from .core.errors import EngineError

_CAMERA_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


@dataclass(frozen=True)
class _BoardError:
    message: str
    readable: int


@dataclass(frozen=True)
class ChessboardResult:
    code: int
    message: str
    photos: int
    readable: int
    rms: float | None = None
    band: str | None = None
    camera_matrix: list[float] | None = None
    dist_coeffs: list[float] | None = None
    image_width: int | None = None
    image_height: int | None = None
    written: bool = False


def valid_camera_id(camera_id: str) -> bool:
    return _CAMERA_ID.fullmatch(camera_id) is not None


def calibrate_folder(
    config_dir: Path,
    folder: Path,
    camera_id: str,
    square_mm: float,
    corners_cols: int,
    corners_rows: int,
) -> tuple[int, str]:
    result = calibrate_report(config_dir, folder, camera_id, square_mm, corners_cols, corners_rows)
    return result.code, result.message


def calibrate_report(
    config_dir: Path,
    folder: Path,
    camera_id: str,
    square_mm: float,
    corners_cols: int,
    corners_rows: int,
) -> ChessboardResult:
    if not valid_camera_id(camera_id):
        return _fail(0, 0, "ID kamera hanya huruf, angka, hubung, atau garis bawah.")
    if square_mm <= 0 or corners_cols < 3 or corners_rows < 3:
        return _fail(0, 0, "Ukuran kotak dan jumlah sudut harus positif. Sudut minimal 3×3.")
    images = _images(folder)
    if not images:
        return _fail(0, 0, f"Tidak ada foto di {folder}.")
    try:
        settings = load_settings(config_dir)
    except EngineError as exc:
        return _fail(len(images), 0, exc.spec.message_id)
    found = _calibrate(images, square_mm, corners_cols, corners_rows)
    if isinstance(found, _BoardError):
        return _fail(len(images), found.readable, found.message)
    rms, matrix, dist, width, height, readable = found
    camera = settings.thresholds.camera
    band = rms_decision(rms, camera.rms_good_px, camera.rms_max_px)
    if band == "reject":
        return ChessboardResult(
            code=1,
            message=(f"RMS {rms:.6f} melewati ambang {camera.rms_max_px}. Berkas tidak ditulis."),
            photos=len(images),
            readable=readable,
            rms=rms,
            band=band,
            camera_matrix=matrix,
            dist_coeffs=dist,
            image_width=width,
            image_height=height,
            written=False,
        )
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
        message = (
            f"Kalibrasi {camera_id} ditulis dengan peringatan. "
            f"RMS {rms:.6f} di atas {camera.rms_good_px} dan tidak di atas {camera.rms_max_px}."
        )
    else:
        message = f"Kalibrasi {camera_id} ditulis. RMS {rms:.6f}."
    return ChessboardResult(
        code=0,
        message=message,
        photos=len(images),
        readable=readable,
        rms=rms,
        band=band,
        camera_matrix=matrix,
        dist_coeffs=dist,
        image_width=width,
        image_height=height,
        written=True,
    )


def chessboard_png(cols: int, rows: int, square_px: int = 48) -> bytes | str:
    """Pola cetak. cols×rows adalah sudut dalam, bukan jumlah kotak."""
    if cols < 3 or rows < 3 or cols > 20 or rows > 20 or square_px < 8:
        return "Sudut dalam harus 3 sampai 20."
    try:
        cv2: Any = importlib.import_module("cv2")
        import numpy as np
    except ImportError:
        return "OpenCV tidak terpasang."
    squares_x = cols + 1
    squares_y = rows + 1
    margin = square_px
    height = squares_y * square_px + 2 * margin
    width = squares_x * square_px + 2 * margin
    image = np.full((height, width), 255, np.uint8)
    for row in range(squares_y):
        for col in range(squares_x):
            if (row + col) % 2 == 0:
                y0 = margin + row * square_px
                x0 = margin + col * square_px
                image[y0 : y0 + square_px, x0 : x0 + square_px] = 0
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        return "Pola papan gagal dibuat."
    return bytes(encoded)


def _fail(photos: int, readable: int, message: str) -> ChessboardResult:
    return ChessboardResult(code=2, message=message, photos=photos, readable=readable)


def _images(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(path for path in folder.iterdir() if path.suffix.lower() in _IMAGE_SUFFIXES)


def _calibrate(
    images: list[Path], square_mm: float, cols: int, rows: int
) -> _BoardError | tuple[float, list[float], list[float], int, int, int]:
    try:
        cv2: Any = importlib.import_module("cv2")
        import numpy as np
    except ImportError:
        return _BoardError("OpenCV tidak terpasang.", 0)
    object_point = _object_points(np, cols, rows, square_mm)
    objects: list[object] = []
    corners: list[object] = []
    size: tuple[int, int] | None = None
    for path in images:
        gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            continue
        height, width = gray.shape[:2]
        if size is None:
            size = (width, height)
        elif size != (width, height):
            return _BoardError(
                "Ukuran foto tidak sama. Semua foto harus satu resolusi.", len(corners)
            )
        ok, found = cv2.findChessboardCorners(gray, (cols, rows), None)
        if not ok:
            continue
        objects.append(object_point)
        corners.append(_refine(cv2, gray, found))
    if len(corners) < 3 or size is None:
        return _BoardError(
            f"Papan catur terbaca pada kurang dari 3 foto ({len(corners)}).", len(corners)
        )
    try:
        rms, matrix, dist, _rvecs, _tvecs = cv2.calibrateCamera(objects, corners, size, None, None)
    except cv2.error:
        return _BoardError(
            "OpenCV menolak kumpulan foto. Ubah pose papan lalu ulangi.", len(corners)
        )
    if not math.isfinite(float(rms)):
        return _BoardError(
            "RMS tidak terbatas. Ulangi dengan pose yang lebih beragam.", len(corners)
        )
    flat_matrix = [float(value) for value in matrix.reshape(-1)]
    flat_dist = [float(value) for value in dist.reshape(-1)]
    width, height = size
    return float(rms), flat_matrix, flat_dist, width, height, len(corners)


def _refine(cv2: Any, gray: object, found: object) -> object:
    """cornerSubPix seperti tutorial: jendela 11, zona nol -1, 30 iterasi, epsilon 0,001."""
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    try:
        refined: object = cv2.cornerSubPix(gray, found, (11, 11), (-1, -1), criteria)
    except cv2.error:
        return found
    return refined


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
