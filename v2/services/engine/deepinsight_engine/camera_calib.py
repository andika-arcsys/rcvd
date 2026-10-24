"""Kalibrasi papan catur dan ChArUco.

Langkah papan catur mengikuti tutorial VisionBrick: cari sudut dalam, haluskan
dengan cornerSubPix (jendela 11×11, 30 iterasi), lalu calibrateCamera.
ChArUco memakai CharucoDetector dan matchImagePoints, lalu calibrateCamera
yang sama. OpenCV di mesin ini tidak punya calibrateCameraCharuco.
Titik objek dikirim dalam meter (milimeter operator dibagi 1000) supaya
solvePnP selaras dengan kedalaman video. Ambang RMS hanya dari config.
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
    *,
    board: str = "chessboard",
    marker_mm: float | None = None,
    port: str = "",
    water: str = "",
) -> ChessboardResult:
    if not valid_camera_id(camera_id):
        return _fail(0, 0, "ID kamera hanya huruf, angka, hubung, atau garis bawah.")
    if square_mm <= 0 or corners_cols < 3 or corners_rows < 3:
        return _fail(0, 0, "Ukuran kotak dan jumlah sudut harus positif. Sudut minimal 3×3.")
    checked = _meta(board, marker_mm, square_mm, port, water)
    if isinstance(checked, str):
        return _fail(0, 0, checked)
    images = _images(folder)
    if not images:
        return _fail(0, 0, f"Tidak ada foto di {folder}.")
    try:
        settings = load_settings(config_dir)
    except EngineError as exc:
        return _fail(len(images), 0, exc.spec.message_id)
    found = _calibrate(images, square_mm, corners_cols, corners_rows, board, marker_mm)
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
        board,
        None if port == "" else port,
        None if water == "" else water,
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


def charuco_png(squares_x: int, squares_y: int, square_mm: float, marker_mm: float) -> bytes | str:
    """Pola ChArUco. squares_x × squares_y adalah jumlah kotak, bukan sudut dalam."""
    if squares_x < 3 or squares_y < 3 or squares_x > 12 or squares_y > 12:
        return "Jumlah kotak ChArUco harus 3 sampai 12."
    if square_mm <= 0 or marker_mm <= 0 or marker_mm >= square_mm:
        return "Sisi marker harus lebih kecil dari sisi kotak."
    try:
        cv2: Any = importlib.import_module("cv2")
    except ImportError:
        return "OpenCV tidak terpasang."
    square_px = 60
    margin = 20
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker_px = square_px * marker_mm / square_mm
    try:
        pattern = cv2.aruco.CharucoBoard(
            (squares_x, squares_y), float(square_px), float(marker_px), dictionary
        )
        image = pattern.generateImage(
            (squares_x * square_px + 2 * margin, squares_y * square_px + 2 * margin),
            marginSize=margin,
        )
    except cv2.error:
        return "Pola ChArUco gagal dibuat. Kamus DICT_4X4_50 tidak muat untuk papan ini."
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        return "Pola ChArUco gagal dibuat."
    return bytes(encoded)


def _meta(
    board: str, marker_mm: float | None, square_mm: float, port: str, water: str
) -> str | None:
    if board not in {"chessboard", "charuco"}:
        return "Papan diisi catur atau ChArUco."
    if port not in {"", "dome", "flat"} or water not in {"", "laut", "tawar"}:
        return "Port diisi kubah, datar, atau dikosongkan. Air diisi laut, tawar, atau dikosongkan."
    if board == "charuco" and (marker_mm is None or marker_mm <= 0 or marker_mm >= square_mm):
        return "Sisi marker ChArUco diukur dalam milimeter dan lebih kecil dari sisi kotak."
    return None


def _calibrate(
    images: list[Path],
    square_mm: float,
    cols: int,
    rows: int,
    board: str,
    marker_mm: float | None,
) -> _BoardError | tuple[float, list[float], list[float], int, int, int]:
    try:
        cv2: Any = importlib.import_module("cv2")
        import numpy as np
    except ImportError:
        return _BoardError("OpenCV tidak terpasang.", 0)
    if board == "charuco":
        return _charuco(cv2, np, images, square_mm, cols, rows, marker_mm)
    return _chessboard(cv2, np, images, square_mm, cols, rows)


def _refine(cv2: Any, gray: object, found: object) -> object:
    """cornerSubPix seperti tutorial: jendela 11, zona nol -1, 30 iterasi, epsilon 0,001."""
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    try:
        refined: object = cv2.cornerSubPix(gray, found, (11, 11), (-1, -1), criteria)
    except cv2.error:
        return found
    return refined


def _chessboard(
    cv2: Any, np: Any, images: list[Path], square_mm: float, cols: int, rows: int
) -> _BoardError | tuple[float, list[float], list[float], int, int, int]:
    object_point = _object_points(np, cols, rows, square_mm)
    objects: list[object] = []
    corners: list[object] = []
    size: tuple[int, int] | None = None
    for path in images:
        gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        loaded = _size(gray, size, len(corners))
        if isinstance(loaded, _BoardError):
            return loaded
        if loaded is None:
            continue
        size = loaded
        ok, found = cv2.findChessboardCorners(gray, (cols, rows), None)
        if not ok:
            continue
        objects.append(object_point)
        corners.append(_refine(cv2, gray, found))
    return _finish(cv2, objects, corners, size, "Papan catur")


def _charuco(
    cv2: Any,
    np: Any,
    images: list[Path],
    square_mm: float,
    cols: int,
    rows: int,
    marker_mm: float | None,
) -> _BoardError | tuple[float, list[float], list[float], int, int, int]:
    if marker_mm is None:
        return _BoardError("Sisi marker ChArUco kosong.", 0)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    try:
        pattern = cv2.aruco.CharucoBoard(
            (cols, rows), square_mm / 1000.0, marker_mm / 1000.0, dictionary
        )
        detector = cv2.aruco.CharucoDetector(pattern)
    except cv2.error:
        return _BoardError("Ukuran papan ChArUco tidak cocok dengan kamus DICT_4X4_50.", 0)
    objects: list[object] = []
    corners: list[object] = []
    size: tuple[int, int] | None = None
    for path in images:
        gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        loaded = _size(gray, size, len(corners))
        if isinstance(loaded, _BoardError):
            return loaded
        if loaded is None:
            continue
        size = loaded
        pair = _charuco_points(cv2, np, detector, pattern, gray)
        if pair is None:
            continue
        objects.append(pair[0])
        corners.append(pair[1])
    return _finish(cv2, objects, corners, size, "Papan ChArUco")


def _size(
    gray: Any, size: tuple[int, int] | None, readable: int
) -> _BoardError | tuple[int, int] | None:
    if gray is None:
        return None
    height, width = gray.shape[:2]
    found = (int(width), int(height))
    if size is not None and size != found:
        return _BoardError("Ukuran foto tidak sama. Semua foto harus satu resolusi.", readable)
    return found


def _charuco_points(
    cv2: Any, np: Any, detector: Any, pattern: Any, gray: Any
) -> tuple[Any, Any] | None:
    detected = detector.detectBoard(gray)
    if not isinstance(detected, tuple) or len(detected) < 2:
        return None
    found, ids = detected[0], detected[1]
    if found is None or ids is None or len(found) < 4:
        return None
    refined = np.asarray(_refine_points(cv2, np, gray, found), dtype=np.float32).reshape(-1, 2)
    try:
        matched = pattern.matchImagePoints(refined, ids)
    except cv2.error:
        return None
    if not isinstance(matched, tuple) or len(matched) < 2:
        return None
    obj, img = matched[0], matched[1]
    if obj is None or img is None or len(obj) < 4:
        return None
    return (
        np.asarray(obj, dtype=np.float32).reshape(-1, 3),
        np.asarray(img, dtype=np.float32).reshape(-1, 1, 2),
    )


def _finish(
    cv2: Any,
    objects: list[object],
    corners: list[object],
    size: tuple[int, int] | None,
    label: str,
) -> _BoardError | tuple[float, list[float], list[float], int, int, int]:
    readable = len(corners)
    if readable < 3 or size is None:
        return _BoardError(f"{label} terbaca pada kurang dari 3 foto ({readable}).", readable)
    try:
        rms, matrix, dist, _rvecs, _tvecs = cv2.calibrateCamera(objects, corners, size, None, None)
    except cv2.error:
        return _BoardError("OpenCV menolak kumpulan foto. Ubah pose papan lalu ulangi.", readable)
    if not math.isfinite(float(rms)):
        return _BoardError("RMS tidak terbatas. Ulangi dengan pose yang lebih beragam.", readable)
    flat_matrix = [float(value) for value in matrix.reshape(-1)]
    flat_dist = [float(value) for value in dist.reshape(-1)]
    width, height = size
    return float(rms), flat_matrix, flat_dist, width, height, len(corners)


def _refine_points(cv2: Any, np: Any, gray: Any, found: Any) -> Any:
    points = np.asarray(found, dtype=np.float32).reshape(-1, 1, 2)
    return _refine(cv2, gray, points)


def _object_points(np: Any, cols: int, rows: int, square_mm: float) -> Any:
    grid = np.zeros((cols * rows, 3), np.float32)
    grid[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2)
    return grid * (float(square_mm) / 1000.0)


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
    board: str,
    port: str | None,
    water: str | None,
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
        board=board,
        port=port,
        water=water,
    )
    target = config_dir / "cameras" / f"{camera_id}.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(payload.model_dump(), sort_keys=False, allow_unicode=True)
    if warn:
        note = "# RMS pada pita peringatan: di atas rms_good_px, tidak di atas rms_max_px.\n"
        body = note + body
    target.write_text(body, encoding="utf-8")
