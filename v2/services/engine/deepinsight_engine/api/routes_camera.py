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

from ..aruco_depth import DICTIONARY, marker_png, measure_markers
from ..camera_calib import calibrate_report, chessboard_png, valid_camera_id
from ..core.camera_file import CameraFile
from ..core.errors import EngineError
from ..office.service import Office
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


class ArucoOut(BaseModel):
    camera_id: str
    marker_mm: float
    dictionary: str
    markers: list[MarkerOut]
    message: str
    preview_jpeg: str | None = None


@camera.get("/cameras/pattern/chessboard")
def chessboard_pattern(cols: int = 8, rows: int = 6) -> Response:
    payload = chessboard_png(cols, rows)
    if isinstance(payload, str):
        raise EngineError("API-002", payload)
    return _png(payload, "papan-catur.png")


@camera.get("/cameras/pattern/aruco")
def aruco_pattern(marker_id: int = 0) -> Response:
    payload = marker_png(marker_id)
    if isinstance(payload, str):
        raise EngineError("API-002", payload)
    return _png(payload, f"aruco-4x4-{marker_id}.png")


@camera.post("/cameras/calibrate", response_model=CalibrationOut)
async def calibrate(
    request: Request,
    role: Annotated[str, Form()],
    camera_id: Annotated[str, Form()],
    square_mm: Annotated[float, Form()],
    corners_cols: Annotated[int, Form()],
    corners_rows: Annotated[int, Form()],
    files: Annotated[list[UploadFile], File()],
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
) -> ArucoOut:
    office, user_id = _require_writer(request, role)
    matrix, dist = _intrinsics(office.config_dir, camera_id.strip())
    payload = await file.read()
    if len(payload) > _MAX_BYTES:
        raise EngineError("API-002", "Foto terlalu besar. Maksimum 20 MB.")
    scan = measure_markers(payload, matrix, dist, marker_mm)
    office.audit(
        "aruco_depth",
        user_id=user_id,
        entity="camera",
        entity_id=camera_id.strip(),
        detail=scan.message,
    )
    preview = None if scan.preview_jpeg is None else base64.b64encode(scan.preview_jpeg).decode()
    return ArucoOut(
        camera_id=camera_id.strip(),
        marker_mm=marker_mm,
        dictionary=DICTIONARY,
        markers=[
            MarkerOut(
                marker_id=item.marker_id,
                x_mm=item.x_mm,
                y_mm=item.y_mm,
                z_mm=item.z_mm,
                distance_mm=item.distance_mm,
            )
            for item in scan.markers
        ],
        message=scan.message,
        preview_jpeg=preview,
    )


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


def _intrinsics(config_dir: Path, camera_id: str) -> tuple[list[float], list[float]]:
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
    return parsed.camera_matrix, parsed.dist_coeffs


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
