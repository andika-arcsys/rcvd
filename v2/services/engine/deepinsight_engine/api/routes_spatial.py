"""Estimasi kedalaman pada frame beku. Tidak mengubah angka simpan 2D."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, ValidationError

from ..core.camera_file import CameraFile
from .routes_measure import PairIn, PolyIn, Px
from .security import require_token

_CAMERA_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,64}$")

spatial = APIRouter(dependencies=[Depends(require_token)], tags=["spatial"])


class PathIn(BaseModel):
    points: list[Px] = Field(min_length=2)


class EstimateIn(BaseModel):
    frame_id: str
    ref_cm: float = Field(gt=0)
    calibration: PairIn
    lengths: list[PairIn] = []
    areas: list[PolyIn] = []
    paths: list[PathIn] = []
    camera_id: str | None = None


class LengthEstimate(BaseModel):
    distance_cm: float
    uncertainty_cm: float
    validity: str
    kind: str = "span"
    tag: str = ""
    depth: float | None = None
    sample_u: float | None = None
    sample_v: float | None = None
    map_u: float | None = None
    map_v: float | None = None
    depth_b: float | None = None
    sample_u_b: float | None = None
    sample_v_b: float | None = None
    map_u_b: float | None = None
    map_v_b: float | None = None
    uncertain_depth: bool = False
    angle_deg: float = 0.0
    warnings: list[str] = []


class AreaEstimate(BaseModel):
    area_cm2: float
    uncertainty_cm2: float
    validity: str


class PathEstimate(BaseModel):
    path_cm: float
    uncertainty_cm: float
    validity: str
    sample_count: int


class EstimateOut(BaseModel):
    frame_id: str
    kind: Literal["spatial-geometry"]
    validity: str
    distance_cm: float
    distance_uncertainty_cm: float
    scale: float
    raw_reference_cm: float
    lengths: list[LengthEstimate]
    areas: list[AreaEstimate]
    paths: list[PathEstimate]
    warnings: list[str]
    units: Literal["METERS"]
    backend: str
    underwater_intrinsics: bool
    focal_px: float | None
    intrinsics_source: str = "longest_side"
    model_id: str = ""
    process_res: int = 0
    resize_method: str = ""
    checkpoint: str = ""
    conf_min: float = 0.0
    cal_depth: float | None = None
    cal_u: float | None = None
    cal_v: float | None = None
    cal_map_u: float | None = None
    cal_map_v: float | None = None
    cal_angle_deg: float = 0.0


@spatial.post("/spatial/estimate", response_model=EstimateOut)
def estimate_depth(body: EstimateIn, request: Request) -> EstimateOut:
    spec = {
        "point_a": [body.calibration.a.x, body.calibration.a.y],
        "point_b": [body.calibration.b.x, body.calibration.b.y],
        "known_m": body.ref_cm / 100.0,
        "lengths": [
            {
                "a": [item.a.x, item.a.y],
                "b": [item.b.x, item.b.y],
                "kind": item.kind,
                "tag": item.tag,
            }
            for item in body.lengths
        ],
        "areas": [[[point.x, point.y] for point in item.points] for item in body.areas],
        "paths": [[[point.x, point.y] for point in item.points] for item in body.paths],
    }
    spec.update(_provenance(request, body.camera_id))
    event = request.app.state.runtime.estimate_spatial(body.frame_id, spec)
    return EstimateOut.model_validate(event)


def _provenance(request: Request, camera_id: str | None) -> dict[str, object]:
    settings = request.app.state.settings
    found: dict[str, object] = {
        "click_sigma_px": settings.thresholds.calibration.click_sigma_px,
        "conf_min": settings.spatialsight.conf_min,
    }
    matrix = _camera_file(request, camera_id)
    if matrix is not None:
        found.update(matrix)
    return found


def _camera_file(request: Request, camera_id: str | None) -> dict[str, object] | None:
    office = request.app.state.office
    chosen = camera_id or _mission_camera(office)
    if chosen is None or not _CAMERA_ID.match(chosen):
        return None
    path = Path(office.config_dir) / "cameras" / f"{chosen}.yaml"
    if not path.is_file():
        return None
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        camera = CameraFile.model_validate(loaded)
    except (OSError, yaml.YAMLError, ValidationError):
        return None
    if camera.camera_matrix is None:
        return None
    return {
        "camera_matrix": camera.camera_matrix,
        "camera_width": camera.image_width,
        "camera_height": camera.image_height,
    }


def _mission_camera(office: object) -> str | None:
    current = getattr(office, "current", None)
    if not callable(current):
        return None
    mission = current()
    camera_id = getattr(mission, "camera_id", None)
    if isinstance(camera_id, str) and camera_id:
        return camera_id
    return None
