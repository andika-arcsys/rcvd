"""Kalibrasi pipa bawah air: sumbu 3D, ukur, dan skala kedalaman. Tanpa menyimpan frame."""

from __future__ import annotations

import base64
import json
import math
from typing import Annotated, Any, Literal

import numpy as np
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import BaseModel, Field

from ..camera_calib import valid_camera_id
from ..core.camera_file import CameraFile
from ..core.errors import EngineError
from ..pipecal import cal4, uncertainty
from ..pipecal.cal3 import (
    AxisModel,
    auto_stations,
    axis_model,
    clip_range,
    silhouettes,
)
from ..pipecal.camera import FrameMismatchError, PipeCamera
from ..pipecal.measure import (
    area,
    axis_param,
    basis,
    clock,
    surface_point,
    surface_width,
    to_cyl,
    unroll,
    up_vector,
)
from .routes_camera import _load_camera, _require_writer
from .security import require_token

pipecal = APIRouter(dependencies=[Depends(require_token)], tags=["kalibrasi-pipa"])
_MAX_TENSOR = 60_000_000

Point = list[float]


class PipeIn(BaseModel):
    role: str
    camera_id: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    diameter_cm: float = Field(gt=0)
    d_type: Literal["pi-tape", "coating", "baja"] = "baja"
    top: list[Point]
    bot: list[Point]
    step_px: float = Field(default=100.0, gt=5)


class StationOut(BaseModel):
    top: Point
    bot: Point
    e: float
    rel_res: float


class SolveOut(BaseModel):
    ok: bool
    message: str
    status: str
    approximate: bool
    psi_deg: float
    res_top_px: float
    res_bot_px: float
    vp: Point
    axis_point: list[float]
    axis_dir: list[float]
    stations: list[StationOut]
    e_max: float
    rel_res_max: float
    angle_deg: float
    spread: float
    passed: bool


class MeasureIn(PipeIn):
    kind: Literal["length", "width", "area", "clock"]
    points: list[Point]
    pitch_deg: float = 0.0
    n_mc: int = Field(default=300, ge=20, le=2000)


class MeasureOut(BaseModel):
    kind: str
    value: float
    unit: str
    p025: float
    p975: float
    clock: int | None = None
    status: str
    mc_runs: int
    approximate: bool


class ProfileOut(BaseModel):
    z: list[float | None]
    theory: list[float | None]
    delta: list[float | None]
    relief_cm: float | None
    target_cm: float
    flagged: list[int]


class DepthOut(BaseModel):
    a: float
    b: float
    kind: str
    err_rel: float
    n_pixels: int
    sigma_cm: float
    status: str
    preview_png: str
    profile: ProfileOut | None = None


def _camera(request: Request, body: PipeIn) -> tuple[PipeCamera, CameraFile]:
    office, _ = _require_writer(request, body.role)
    if not valid_camera_id(body.camera_id):
        raise EngineError("API-002", "ID kamera tidak valid.")
    file = _load_camera(office.config_dir, body.camera_id)
    try:
        return PipeCamera.from_file(file, body.width, body.height), file
    except FrameMismatchError as exc:
        raise EngineError("API-002", str(exc)) from exc


def _solve(
    cam: PipeCamera, body: PipeIn, radius: float
) -> tuple[Any, AxisModel, list[tuple[np.ndarray, np.ndarray]]]:
    if len(body.top) < 3 or len(body.bot) < 3:
        raise EngineError("API-002", "Klik minimal 3 titik di tiap tepi pipa.")
    sil = silhouettes(cam, body.top, body.bot)
    rng = clip_range(sil.l_top, body.width, body.height)
    if rng is None:
        raise EngineError("API-002", "Tepi atas keluar dari frame.")
    lo = max(rng[0], float(sil.top_ud[:, 0].min()), float(sil.bot_ud[:, 0].min()))
    hi = min(rng[1], float(sil.top_ud[:, 0].max()), float(sil.bot_ud[:, 0].max()))
    if hi - lo < 20:
        raise EngineError("API-002", "Titik klik terlalu rapat. Sebar sepanjang pipa.")
    step = min(body.step_px, (hi - lo) / 5)
    pairs = auto_stations(sil.l_top, sil.l_bot, sil.vp, (lo, hi), step)
    if len(pairs) < 3:
        raise EngineError("API-002", "Stasiun kurang dari 3. Perkecil langkah piksel.")
    return sil, axis_model(cam, sil, pairs, radius), pairs


def _fail(exc: Exception) -> EngineError:
    return EngineError("API-002", f"Perhitungan gagal: {exc}")


@pipecal.post("/pipecal/solve", response_model=SolveOut)
def solve(request: Request, body: PipeIn) -> SolveOut:
    cam, _file = _camera(request, body)
    try:
        sil, model, pairs = _solve(cam, body, body.diameter_cm / 2)
    except (ValueError, np.linalg.LinAlgError) as exc:
        raise _fail(exc) from exc
    cal2_ok = sil.res_top < 3.0 and sil.res_bot < 3.0
    status = uncertainty.status(
        not cam.approximate, cal2_ok, model.passed, body.d_type, len(model.stations)
    )
    message = "Sumbu lolos uji CAL 3." if model.passed else "Sumbu belum lolos uji CAL 3."
    return SolveOut(
        ok=True,
        message=message,
        status=status,
        approximate=cam.approximate,
        psi_deg=float(sil.psi),
        res_top_px=float(sil.res_top),
        res_bot_px=float(sil.res_bot),
        vp=[float(x) for x in sil.vp],
        axis_point=[float(x) for x in model.c],
        axis_dir=[float(x) for x in model.d],
        stations=[
            StationOut(
                top=[float(x) for x in cam.to_raw_px(pt[None])[0]],
                bot=[float(x) for x in cam.to_raw_px(pb[None])[0]],
                e=float(model.e[i]),
                rel_res=float(model.rel_res[i]),
            )
            for i, (pt, pb) in enumerate(pairs)
        ],
        e_max=float(model.e.max()),
        rel_res_max=float(model.rel_res.max()),
        angle_deg=float(model.angle_deg),
        spread=float(model.spread),
        passed=bool(model.passed),
    )


def _measure_once(
    cam: PipeCamera, body: MeasureIn, top: Any, bot: Any, pts: Any, radius: float
) -> tuple[float, int | None]:
    probe = body.model_copy(update={"top": [list(p) for p in top], "bot": [list(p) for p in bot]})
    _sil, model, _pairs = _solve(cam, probe, radius)
    c, d = model.c, model.d
    if body.kind == "length":
        r = cam.rays(pts)
        return abs(axis_param(r[1], c, d) - axis_param(r[0], c, d)), None
    e1, e2 = basis(d, up_vector(body.pitch_deg))
    if body.kind == "clock":
        p = surface_point(cam, pts[0], c, d, radius)
        _t, phi = to_cyl(p, c, d, e1, e2)
        return math.degrees(phi) % 360.0, clock(phi)
    xy = unroll(cam, pts, c, d, radius, e1, e2)
    return (surface_width(xy) if body.kind == "width" else area(xy)), None


@pipecal.post("/pipecal/measure", response_model=MeasureOut)
def measure(request: Request, body: MeasureIn) -> MeasureOut:
    cam, _file = _camera(request, body)
    need = {"length": 2, "width": 2, "clock": 1, "area": 3}[body.kind]
    if len(body.points) < need or (body.kind != "area" and len(body.points) != need):
        raise EngineError("API-002", f"Jenis ukur ini butuh {need} titik.")
    radius = body.diameter_cm / 2
    n_top, n_bot = len(body.top), len(body.bot)
    try:
        value, hour = _measure_once(cam, body, body.top, body.bot, body.points, radius)
        sil, model, _pairs = _solve(cam, body, radius)
    except (ValueError, np.linalg.LinAlgError) as exc:
        raise _fail(exc) from exc

    def run(edges: list[np.ndarray], kf: float, kd: float) -> float:
        scaled = cam.scaled(kf)
        top, bot, pts = edges[:n_top], edges[n_top : n_top + n_bot], edges[n_top + n_bot :]
        return _measure_once(scaled, body, top, bot, pts, radius * kd)[0]

    d_rel = uncertainty.DIAMETER_REL[body.d_type]
    try:
        med, lo, hi, runs = uncertainty.monte_carlo(
            run,
            [*body.top, *body.bot, *body.points],
            d_rel=d_rel,
            n=body.n_mc,
        )
    except ValueError as exc:
        raise _fail(exc) from exc
    cal2_ok = sil.res_top < 3.0 and sil.res_bot < 3.0
    status = uncertainty.status(
        not cam.approximate, cal2_ok, model.passed, body.d_type, len(model.stations)
    )
    unit = {"length": "cm", "width": "cm", "area": "cm²", "clock": "°"}[body.kind]
    return MeasureOut(
        kind=body.kind,
        value=float(value),
        unit=unit,
        p025=lo,
        p975=hi,
        clock=hour,
        status=status,
        mc_runs=runs,
        approximate=cam.approximate,
    )


@pipecal.post("/pipecal/depth", response_model=DepthOut)
async def depth(
    request: Request,
    role: Annotated[str, Form()],
    camera_id: Annotated[str, Form()],
    width: Annotated[int, Form()],
    height: Annotated[int, Form()],
    diameter_cm: Annotated[float, Form()],
    top: Annotated[str, Form()],
    bot: Annotated[str, Form()],
    tensor: Annotated[UploadFile, File()],
    kind: Annotated[str, Form()] = "disparity",
    d_type: Annotated[str, Form()] = "baja",
    profile_points: Annotated[str, Form()] = "[]",
) -> DepthOut:
    if kind not in {"disparity", "depth"}:
        raise EngineError("API-002", "Jenis model harus disparity atau depth.")
    raw = await tensor.read(_MAX_TENSOR + 1)
    if len(raw) > _MAX_TENSOR:
        raise EngineError("API-002", "Tensor terlalu besar.")
    try:
        edges = PipeIn(
            role=role,
            camera_id=camera_id,
            width=width,
            height=height,
            diameter_cm=diameter_cm,
            d_type=d_type,
            top=json.loads(top),
            bot=json.loads(bot),
        )
        pts = json.loads(profile_points)
    except (ValueError, TypeError) as exc:
        raise EngineError("API-002", "Format titik tidak valid.") from exc
    cam, _file = _camera(request, edges)
    radius = edges.diameter_cm / 2
    try:
        m = cal4.load_tensor(raw)
        if m.shape != (height, width):
            raise EngineError(
                "API-002",
                f"Tensor {m.shape[1]}×{m.shape[0]} tidak sama dengan frame {width}×{height}.",
            )
        _sil, model, _pairs = _solve(cam, edges, radius)
        fit = cal4.run_fit(cam, m, model.c, model.d, radius, kind)
        prof = cal4.profile(cam, pts, m, fit, model.c, model.d, radius) if len(pts) >= 3 else None
    except (ValueError, np.linalg.LinAlgError) as exc:
        raise _fail(exc) from exc
    status = "VALID-TERBATAS" if model.passed and fit.error < 0.1 else "ESTIMASI"
    return DepthOut(
        a=fit.a,
        b=fit.b,
        kind=fit.kind,
        err_rel=fit.error,
        n_pixels=fit.points,
        sigma_cm=fit.sigma_cm,
        status=status,
        preview_png=base64.b64encode(cal4.turbo_preview(m)).decode("ascii"),
        profile=ProfileOut(**prof) if prof else None,
    )
