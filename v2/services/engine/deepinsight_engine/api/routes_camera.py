"""Unggah foto papan catur dan ukur kedalaman marker ArUco."""

from __future__ import annotations

import base64
import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Annotated

import yaml
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ValidationError

from ..aruco_depth import DICTIONARIES, DICTIONARY, ArucoScan, marker_png, measure_markers
from ..camera_calib import calibrate_report, charuco_png, chessboard_png, valid_camera_id
from ..core.camera_file import CameraFile
from ..core.errors import EngineError
from ..k3_align import alignment_status
from ..office.service import Office
from ..reference_camera import reference_camera
from ..spatial.da3_frame import camera_k
from .security import require_token

camera = APIRouter(dependencies=[Depends(require_token)], tags=["kamera"])
_WRITERS = frozenset({"ketua_tim", "pilot_drone", "ahli_ukur", "teknisi_program"})
_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
_MAX_BYTES = 20_000_000
_MAX_FILES = 40


class CalibrationOut(BaseModel):
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
    written: bool


class MarkerOut(BaseModel):
    marker_id: int
    x_mm: float
    y_mm: float
    z_mm: float
    distance_mm: float
    center_u: float = 0.0
    center_v: float = 0.0
    corners: list[list[float]] = []
    axis: list[list[float]] = []


class K3Out(BaseModel):
    camera_id: str
    a: float | None = None
    b: float | None = None
    samples: int
    ready: bool


class ArucoOut(BaseModel):
    camera_id: str
    marker_mm: float
    dictionary: str
    markers: list[MarkerOut]
    message: str
    preview_jpeg: str | None = None
    frame_width: int = 0
    frame_height: int = 0


class ReferenceOut(BaseModel):
    id: str
    origin: str
    board: str | None = None
    square_mm: float | None = None
    corners_cols: int | None = None
    corners_rows: int | None = None
    image_width: int | None = None
    image_height: int | None = None
    marker_mm: float | None = None
    dictionary: str | None = None
    camera_matrix: list[float]
    dist_coeffs: list[float]
    focal_px: float
    principal_u: float
    principal_v: float
    marker_source_cm: float | None = None
    calibrated_underwater: bool
    matches_formula: bool


@camera.get("/cameras/pattern/chessboard")
def chessboard_pattern(cols: int = 9, rows: int = 6) -> Response:
    payload = chessboard_png(cols, rows)
    if isinstance(payload, str):
        raise EngineError("API-002", payload)
    return _png(payload, "papan-catur.png")


@camera.get("/cameras/pattern/aruco")
def aruco_pattern(marker_id: int = 0, dictionary: str = DICTIONARY) -> Response:
    payload = marker_png(marker_id, dictionary_name=dictionary)
    if isinstance(payload, str):
        raise EngineError("API-002", payload)
    slug = "6x6" if dictionary == "DICT_6X6_250" else "4x4"
    return _png(payload, f"aruco-{slug}-{marker_id}.png")


@camera.get("/cameras/pattern/charuco")
def charuco_pattern(
    squares_x: int = 8, squares_y: int = 6, square_mm: float = 0, marker_mm: float = 0
) -> Response:
    payload = charuco_png(squares_x, squares_y, square_mm, marker_mm)
    if isinstance(payload, str):
        raise EngineError("API-002", payload)
    return _png(payload, "papan-charuco.png")


@camera.get("/cameras/reference", response_model=ReferenceOut)
def camera_reference(request: Request) -> ReferenceOut:
    settings = request.app.state.settings
    formula = reference_camera(settings)
    shown = _stored_reference(request, formula)
    matrix = shown.camera_matrix or formula.camera_matrix or []
    dist = shown.dist_coeffs or formula.dist_coeffs or []
    return ReferenceOut(
        id=shown.id,
        origin=shown.origin or "",
        board=shown.board,
        square_mm=shown.square_mm,
        corners_cols=shown.corners_cols,
        corners_rows=shown.corners_rows,
        image_width=shown.image_width,
        image_height=shown.image_height,
        marker_mm=shown.marker_mm,
        dictionary=shown.dictionary,
        camera_matrix=matrix,
        dist_coeffs=dist,
        focal_px=float(matrix[0]),
        principal_u=float(matrix[2]),
        principal_v=float(matrix[5]),
        marker_source_cm=settings.thresholds.laser.ref_cm,
        calibrated_underwater=shown.origin != "reference",
        matches_formula=shown.model_dump() == formula.model_dump(),
    )


@camera.get("/cameras/k3", response_model=K3Out)
def k3_profile(request: Request, camera_id: str) -> K3Out:
    office, _user_id = _actor(request)
    if not valid_camera_id(camera_id):
        raise EngineError("API-002", "ID kamera tidak valid.")
    status = alignment_status(Path(office.config_dir) / "calibration" / f"{camera_id}.json")
    return K3Out(
        camera_id=camera_id,
        a=status.a,
        b=status.b,
        samples=status.samples,
        ready=status.a is not None and status.b is not None,
    )


@camera.post("/cameras/calibrate", response_model=CalibrationOut)
async def calibrate(
    request: Request,
    role: Annotated[str, Form()],
    camera_id: Annotated[str, Form()],
    square_mm: Annotated[float, Form()],
    corners_cols: Annotated[int, Form()],
    corners_rows: Annotated[int, Form()],
    files: Annotated[list[UploadFile], File()],
    board: Annotated[str, Form()] = "chessboard",
    marker_mm: Annotated[float | None, Form()] = None,
    port: Annotated[str, Form()] = "",
    water: Annotated[str, Form()] = "",
) -> CalibrationOut:
    office, user_id = _require_writer(request, role)
    with tempfile.TemporaryDirectory(prefix="kalibrasi-") as tmp:
        problem = await _save(files, Path(tmp))
        if problem is not None:
            return CalibrationOut(code=2, message=problem, photos=0, readable=0, written=False)
        result = calibrate_report(
            office.config_dir,
            Path(tmp),
            camera_id.strip(),
            square_mm,
            corners_cols,
            corners_rows,
            board=board,
            marker_mm=marker_mm,
            port=port,
            water=water,
        )
    office.audit(
        "camera_calibrated",
        user_id=user_id,
        entity="camera",
        entity_id=camera_id.strip(),
        detail=result.message,
    )
    return CalibrationOut(
        code=result.code,
        message=result.message,
        photos=result.photos,
        readable=result.readable,
        rms=result.rms,
        band=result.band,
        camera_matrix=result.camera_matrix,
        dist_coeffs=result.dist_coeffs,
        image_width=result.image_width,
        image_height=result.image_height,
        written=result.written,
    )


@camera.post("/cameras/aruco", response_model=ArucoOut)
async def aruco_depth(
    request: Request,
    role: Annotated[str, Form()],
    camera_id: Annotated[str, Form()],
    marker_mm: Annotated[float, Form()],
    file: Annotated[UploadFile, File()],
    dictionary: Annotated[str, Form()] = DICTIONARY,
) -> ArucoOut:
    office, user_id = _require_writer(request, role)
    if dictionary not in DICTIONARIES:
        raise EngineError("API-002", "Kamus marker tidak dikenal.")
    camera = _load_camera(office.config_dir, camera_id.strip())
    payload = await file.read()
    if len(payload) > _MAX_BYTES:
        raise EngineError("API-002", "Foto terlalu besar. Maksimum 20 MB.")
    _remember_if_changed(office.config_dir, camera, marker_mm, dictionary)
    scan = measure_markers(
        payload,
        camera.camera_matrix or [],
        camera.dist_coeffs or [],
        marker_mm,
        dictionary,
    )
    office.audit(
        "aruco_depth",
        user_id=user_id,
        entity="camera",
        entity_id=camera_id.strip(),
        detail=scan.message,
    )
    return _scan_out(camera_id.strip(), marker_mm, dictionary, scan)


@camera.post("/cameras/aruco/live", response_model=ArucoOut)
def aruco_live(
    request: Request,
    role: Annotated[str, Form()],
    camera_id: Annotated[str, Form()],
    marker_mm: Annotated[float, Form()],
    dictionary: Annotated[str, Form()] = DICTIONARY,
) -> ArucoOut:
    """Pose marker pada bingkai sumber video yang sedang jalan."""
    _office, _user_id = _require_writer(request, role)
    if dictionary not in DICTIONARIES:
        raise EngineError("API-002", "Kamus marker tidak dikenal.")
    chosen = camera_id.strip()
    camera = _load_camera(request.app.state.office.config_dir, chosen)
    grabbed = request.app.state.runtime.current_frame_jpeg()
    if grabbed is None:
        return ArucoOut(
            camera_id=chosen,
            marker_mm=marker_mm,
            dictionary=dictionary,
            markers=[],
            message=(
                "Sumber video belum punya gambar. Buka kamera laptop, berkas video, atau RTSP."
            ),
        )
    payload, width, height = grabbed
    matrix = _matrix_for_frame(camera, width, height)
    _remember_if_changed(request.app.state.office.config_dir, camera, marker_mm, dictionary)
    scan = measure_markers(payload, matrix, camera.dist_coeffs or [], marker_mm, dictionary)
    return _scan_out(chosen, marker_mm, dictionary, scan)


def _png(payload: bytes, name: str) -> Response:
    return Response(
        content=payload,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


def _require_writer(request: Request, role: str) -> tuple[Office, str]:
    office, user_id = _actor(request)
    if role not in _WRITERS or role not in _known_roles(request, office).get(user_id, []):
        raise EngineError("API-002", "Peran ini tidak boleh menulis kalibrasi kamera.")
    return office, user_id


def _actor(request: Request) -> tuple[Office, str]:
    office = request.app.state.office
    if not isinstance(office, Office) or not office.user_id:
        raise EngineError("AUTH-001", "sesi")
    return office, office.user_id


def _known_roles(request: Request, office: Office) -> dict[str, list[str]]:
    found = {item.id: list(item.roles) for item in request.app.state.settings.users.users}
    with office.db.connect() as conn:
        if not isinstance(conn, sqlite3.Connection):
            raise EngineError("SYS-002", "peran")
        for row in conn.execute("SELECT id, roles_json FROM local_users"):
            loaded = json.loads(str(row["roles_json"]))
            if isinstance(loaded, list):
                found[str(row["id"])] = [str(item) for item in loaded]
    return found


def _scan_out(camera_id: str, marker_mm: float, dictionary: str, scan: ArucoScan) -> ArucoOut:
    preview = None if scan.preview_jpeg is None else base64.b64encode(scan.preview_jpeg).decode()
    return ArucoOut(
        camera_id=camera_id,
        marker_mm=marker_mm,
        dictionary=dictionary,
        markers=[
            MarkerOut(
                marker_id=item.marker_id,
                x_mm=item.x_mm,
                y_mm=item.y_mm,
                z_mm=item.z_mm,
                distance_mm=item.distance_mm,
                center_u=item.center_u,
                center_v=item.center_v,
                corners=_pairs(item.corners),
                axis=_pairs(item.axis),
            )
            for item in scan.markers
        ],
        message=scan.message,
        preview_jpeg=preview,
        frame_width=scan.width,
        frame_height=scan.height,
    )


def _pairs(points: tuple[tuple[float, float], ...]) -> list[list[float]]:
    return [[point[0], point[1]] for point in points]


def _matrix_for_frame(camera: CameraFile, width: int, height: int) -> list[float]:
    matrix = camera.camera_matrix or []
    fx, fy, cx, cy = camera_k(matrix, width, height, camera.image_width, camera.image_height)
    return [fx, 0.0, cx, 0.0, fy, cy, 0.0, 0.0, 1.0]


def _remember_if_changed(
    config_dir: Path, camera: CameraFile, marker_mm: float, dictionary: str
) -> None:
    same_length = camera.marker_mm is not None and abs(camera.marker_mm - marker_mm) < 1e-6
    if same_length and camera.dictionary == dictionary:
        return
    _remember_marker(config_dir, camera.id, marker_mm, dictionary)


def _remember_marker(config_dir: Path, camera_id: str, marker_mm: float, dictionary: str) -> None:
    path = config_dir / "cameras" / f"{camera_id}.yaml"
    text = path.read_text(encoding="utf-8")
    parsed = CameraFile.model_validate(yaml.safe_load(text))
    updated = parsed.model_copy(update={"marker_mm": marker_mm, "dictionary": dictionary})
    comment = "".join(line for line in text.splitlines(True) if line.startswith("#"))
    body = yaml.safe_dump(updated.model_dump(), sort_keys=False, allow_unicode=True)
    path.write_text(comment + body, encoding="utf-8")


def _stored_reference(request: Request, formula: CameraFile) -> CameraFile:
    office = request.app.state.office
    path = Path(office.config_dir) / "cameras" / f"{formula.id}.yaml"
    if not path.is_file():
        return formula
    try:
        loaded = CameraFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except (OSError, yaml.YAMLError, ValidationError):
        return formula
    if loaded.camera_matrix is None or loaded.dist_coeffs is None:
        return formula
    return loaded


def _load_camera(config_dir: Path, camera_id: str) -> CameraFile:
    if not valid_camera_id(camera_id):
        raise EngineError("API-002", "ID kamera tidak valid.")
    path = config_dir / "cameras" / f"{camera_id}.yaml"
    if not path.is_file():
        raise EngineError(
            "API-002", "Berkas kamera belum ada. Hitung kalibrasi papan catur lebih dulu."
        )
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    try:
        parsed = CameraFile.model_validate(raw)
    except ValidationError as exc:
        raise EngineError("API-002", "Berkas kamera tidak lengkap.") from exc
    if parsed.camera_matrix is None or parsed.dist_coeffs is None:
        raise EngineError("API-002", "Berkas kamera belum berisi matriks.")
    return parsed


async def _save(files: list[UploadFile], folder: Path) -> str | None:
    if len(files) > _MAX_FILES:
        return f"Maksimum {_MAX_FILES} foto sekali unggah."
    kept = 0
    for upload in files:
        suffix = Path(upload.filename or "foto.jpg").suffix.lower()
        if suffix not in _SUFFIXES:
            continue
        payload = await upload.read()
        if len(payload) > _MAX_BYTES:
            return "Foto terlalu besar. Maksimum 20 MB per berkas."
        if not payload:
            continue
        (folder / f"{kept:03d}{suffix}").write_bytes(payload)
        kept += 1
    if kept == 0:
        return "Tidak ada foto."
    return None
