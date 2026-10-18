"""Laporan, PIMS, metrik, arsip, pengaturan, dan penutupan."""

from __future__ import annotations

import json
import time
from pathlib import Path

from argon2 import PasswordHasher
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..core.errors import EngineError
from ..office.phase9 import (
    add_local_user,
    advance_report,
    build_report,
    confirmed_rows,
    list_packages,
    override_value,
    patch_setting,
    pdf_bytes,
    queue_retrain,
    release_model,
    revise_report,
    seal_package,
    training_count,
    update_report,
    verify_package,
)
from ..office.service import Office
from .security import require_token

phase9 = APIRouter(dependencies=[Depends(require_token)], tags=["laporan"])
_HASHER = PasswordHasher()


class FindingOut(BaseModel):
    title: str
    class_name: str | None
    span_m: float | None


class ReportOut(BaseModel):
    id: int
    number: str
    mission_id: str
    revision: int
    status: str
    summary: str
    recommendation: str
    locked: bool
    findings: list[FindingOut]
    stages: list[str]


class TextIn(BaseModel):
    summary: str
    recommendation: str


class StageIn(BaseModel):
    role: str


class PackageOut(BaseModel):
    id: str
    name: str
    created_at: str
    manifest_sha: str
    upload: str
    snapshot_count: int
    report_count: int
    bytes: int


class VerifyOut(BaseModel):
    status: str
    manifest_sha: str


class PimsOut(BaseModel):
    procedure_ready: bool
    message: str | None
    prior_position: str | None
    after_position: str | None
    interval_low: int
    interval_low_to_moderate: int
    interval_moderate: int


class MonthOut(BaseModel):
    month: str
    missions: int


class SustainOut(BaseModel):
    hours: float | None
    cost: float | None
    emission: float | None
    findings: int
    months: list[MonthOut]


class MetricOut(BaseModel):
    class_name: str
    precision: float | None
    recall: float | None
    map50: float | None


class AiOut(BaseModel):
    metrics_ready: bool
    metrics: list[MetricOut]
    training: int
    release: str | None


class ReleaseIn(BaseModel):
    role: str
    name: str
    version: str


class SettingOut(BaseModel):
    laser_ref_cm: float | None
    rod_length_m: float
    rod_tolerance_pct: float
    freeze_max_delta_cm: float
    rope_tolerance_pct: float
    critical_inch_16: float
    critical_inch_8: float
    presets: list[str]
    upload_dir: str | None
    models_dir: str
    users: list[str]


class PatchIn(BaseModel):
    role: str
    key: str
    value: str


class UserIn(BaseModel):
    role: str
    user_id: str = Field(min_length=1)
    name: str
    pin: str = Field(min_length=6, max_length=6)
    roles: list[str]


class SummaryOut(BaseModel):
    duration_s: float
    snapshots: int
    stored_bytes: int
    findings: int


class SealOut(BaseModel):
    recording_stopped: bool
    packaged: bool
    hashed: bool
    upload: str
    package_id: str
    package_sha256: str


@phase9.get("/reports", response_model=list[ReportOut])
def reports(request: Request) -> list[ReportOut]:
    with request.app.state.office.db.connect() as conn:
        rows = conn.execute("SELECT * FROM reports ORDER BY id").fetchall()
        return [_report_view(conn, row) for row in rows]


@phase9.post("/reports", response_model=ReportOut)
def create_report(body: StageIn, request: Request) -> ReportOut:
    office, user_id = _actor(request)
    mission = office.current()
    mission_id = mission.id if mission is not None else request.app.state.session_id
    with office.db.connect() as conn:
        report_id = build_report(conn, mission_id, user_id, body.role)
        row = conn.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
        view = _report_view(conn, row)
    _audit(request, "report_draft", view.number)
    return view


@phase9.put("/reports/{report_id}", response_model=ReportOut)
def edit_report(report_id: int, body: TextIn, request: Request) -> ReportOut:
    office, user_id = _actor(request)
    with office.db.connect() as conn:
        update_report(conn, report_id, body.summary, body.recommendation)
        row = conn.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
        return _report_view(conn, row)


@phase9.post("/reports/{report_id}/stage", response_model=ReportOut)
def stage_report(report_id: int, body: StageIn, request: Request) -> ReportOut:
    office, user_id = _actor(request)
    with office.db.connect() as conn:
        advance_report(conn, report_id, user_id, body.role, _roles(request, conn))
        row = conn.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
        view = _report_view(conn, row)
    _audit(request, "report_stage", view.number)
    return view


@phase9.post("/reports/{report_id}/revise", response_model=ReportOut)
def revise(report_id: int, body: StageIn, request: Request) -> ReportOut:
    office, user_id = _actor(request)
    with office.db.connect() as conn:
        new_id = revise_report(conn, report_id, user_id, body.role)
        row = conn.execute("SELECT * FROM reports WHERE id=?", (new_id,)).fetchone()
        return _report_view(conn, row)


@phase9.get("/reports/{report_id}/pdf")
def report_pdf(report_id: int, request: Request) -> Response:
    with request.app.state.office.db.connect() as conn:
        row = conn.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
        if row is None:
            raise EngineError("API-003", str(report_id))
        lines = [str(row["number"]), str(row["summary"]), str(row["recommendation"])]
    return Response(content=pdf_bytes(lines), media_type="application/pdf")


@phase9.get("/pims", response_model=PimsOut)
def pims(request: Request) -> PimsOut:
    settings = request.app.state.settings
    years = settings.thresholds.inspection_interval_years
    ready = bool(settings.procedure.complete)
    return PimsOut(
        procedure_ready=ready,
        message=None if ready else "Data prosedur belum diisi",
        prior_position=settings.procedure.prior_position if ready else None,
        after_position=None,
        interval_low=years.low,
        interval_low_to_moderate=years.low_to_moderate,
        interval_moderate=years.moderate_and_above,
    )


@phase9.get("/sustainability", response_model=SustainOut)
def sustainability(request: Request) -> SustainOut:
    with request.app.state.office.db.connect() as conn:
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM review_items WHERE queue_status='confirmed'"
        ).fetchone()
        months = conn.execute(
            "SELECT substr(created_at, 1, 7) AS month, COUNT(*) AS n FROM missions "
            "WHERE created_at IS NOT NULL GROUP BY month"
        ).fetchall()
    return SustainOut(
        hours=None,
        cost=None,
        emission=None,
        findings=int(count["n"]) if count else 0,
        months=[MonthOut(month=str(row["month"]), missions=int(row["n"])) for row in months],
    )


@phase9.get("/ai/metrics", response_model=AiOut)
def ai_metrics(request: Request) -> AiOut:
    settings = request.app.state.settings
    metrics = _metrics(settings, Path(request.app.state.office.config_dir))
    with request.app.state.office.db.connect() as conn:
        training = training_count(conn)
        release = conn.execute(
            "SELECT name, version FROM model_releases ORDER BY id DESC LIMIT 1"
        ).fetchone()
    label = None if release is None else f"{release['name']} {release['version']}"
    return AiOut(metrics_ready=bool(metrics), metrics=metrics, training=training, release=label)


@phase9.post("/ai/retrain")
def retrain(request: Request) -> dict[str, int]:
    office, user_id = _actor(request)
    with office.db.connect() as conn:
        row_id = queue_retrain(conn, user_id)
    _audit(request, "retrain_queued", str(row_id))
    return {"id": row_id}


@phase9.post("/ai/release")
def release(body: ReleaseIn, request: Request) -> dict[str, int]:
    office, user_id = _actor(request)
    with office.db.connect() as conn:
        row_id = release_model(
            conn, user_id, body.role, _roles(request, conn), body.name, body.version
        )
    _audit(request, "model_released", body.version)
    return {"id": row_id}


@phase9.get("/archive", response_model=list[PackageOut])
def archive(request: Request) -> list[PackageOut]:
    with request.app.state.office.db.connect() as conn:
        return [_package(row) for row in list_packages(conn)]


@phase9.post("/archive/{package_id}/verify", response_model=VerifyOut)
def archive_verify(package_id: str, request: Request) -> VerifyOut:
    with request.app.state.office.db.connect() as conn:
        status = verify_package(conn, package_id)
        row = conn.execute("SELECT manifest_sha FROM packages WHERE id=?", (package_id,)).fetchone()
    _audit(request, "package_verified", package_id)
    return VerifyOut(status=status, manifest_sha="" if row is None else str(row["manifest_sha"]))


@phase9.get("/settings", response_model=SettingOut)
def settings_view(request: Request) -> SettingOut:
    settings = request.app.state.settings
    thresholds = settings.thresholds
    with request.app.state.office.db.connect() as conn:
        upload = override_value(conn, "upload_dir")
        local = conn.execute("SELECT id FROM local_users").fetchall()
    names = [item.id for item in settings.users.users]
    names.extend(str(row["id"]) for row in local)
    return SettingOut(
        laser_ref_cm=thresholds.laser.ref_cm,
        rod_length_m=thresholds.rod_test.length_m,
        rod_tolerance_pct=thresholds.rod_test.tolerance_pct,
        freeze_max_delta_cm=thresholds.freeze.max_delta_cm,
        rope_tolerance_pct=thresholds.span.rope_tolerance_pct,
        critical_inch_16=thresholds.span.critical_limit_m.inch_16,
        critical_inch_8=thresholds.span.critical_limit_m.inch_8,
        presets=sorted(settings.aquaclear.presets),
        upload_dir=upload,
        models_dir=settings.app.models.dir,
        users=names,
    )


@phase9.put("/settings", response_model=SettingOut)
def settings_patch(body: PatchIn, request: Request) -> SettingOut:
    office, user_id = _actor(request)
    with office.db.connect() as conn:
        updated, previous = patch_setting(
            conn,
            request.app.state.settings,
            user_id,
            body.role,
            _roles(request, conn),
            body.key,
            body.value,
        )
    request.app.state.settings = updated
    office.settings = updated
    if body.key == "models_dir":
        request.app.state.runtime.set_models_dir(office.config_dir, body.value.strip())
    old = "null" if previous is None else previous
    _audit(request, "settings_changed", f"{body.key}|lama={old}|baru={body.value}")
    return settings_view(request)


@phase9.post("/settings/users", response_model=SettingOut)
def settings_user(body: UserIn, request: Request) -> SettingOut:
    office, user_id = _actor(request)
    digest = _HASHER.hash(body.pin)
    with office.db.connect() as conn:
        add_local_user(
            conn,
            body.user_id,
            body.name,
            digest,
            body.roles,
            user_id,
            body.role,
            _roles(request, conn),
        )
    _audit(request, "user_added", body.user_id)
    return settings_view(request)


@phase9.get("/session/summary", response_model=SummaryOut)
def session_summary(request: Request) -> SummaryOut:
    data_dir = Path(request.app.state.data_dir)
    snaps = data_dir / "snapshots"
    files = [path for path in snaps.glob("*") if path.is_file()] if snaps.is_dir() else []
    with request.app.state.office.db.connect() as conn:
        findings = conn.execute("SELECT COUNT(*) AS n FROM review_items").fetchone()
    return SummaryOut(
        duration_s=round(time.monotonic() - request.app.state.started, 3),
        snapshots=len([path for path in files if path.suffix == ".json"]),
        stored_bytes=sum(path.stat().st_size for path in files),
        findings=int(findings["n"]) if findings else 0,
    )


@phase9.post("/session/seal", response_model=SealOut)
def session_seal(request: Request) -> SealOut:
    office, user_id = _actor(request)
    request.app.state.runtime.close_session()
    with office.db.connect() as conn:
        upload = override_value(conn, "upload_dir")
        row = seal_package(
            conn,
            Path(request.app.state.data_dir),
            request.app.state.session_id,
            upload,
        )
    _audit(request, "package_sealed", str(row["id"]))
    return SealOut(
        recording_stopped=True,
        packaged=True,
        hashed=True,
        upload=str(row["upload"]),
        package_id=str(row["id"]),
        package_sha256=str(row["manifest_sha"]),
    )


def _actor(request: Request) -> tuple[Office, str]:
    office = request.app.state.office
    if not isinstance(office, Office):
        raise EngineError("AUTH-001", "sesi")
    user_id = office.user_id
    if not user_id:
        raise EngineError("AUTH-001", "sesi")
    return office, user_id


def _roles(request: Request, conn: object) -> dict[str, list[str]]:
    import sqlite3

    if not isinstance(conn, sqlite3.Connection):
        raise EngineError("SYS-002", "peran")
    found = {item.id: list(item.roles) for item in request.app.state.settings.users.users}
    for row in conn.execute("SELECT id, roles_json FROM local_users"):
        loaded = json.loads(str(row["roles_json"]))
        found[str(row["id"])] = [str(item) for item in loaded] if isinstance(loaded, list) else []
    return found


def _audit(request: Request, action: str, detail: str) -> None:
    office = request.app.state.office
    user = office.user_id if isinstance(office, Office) else None
    office.audit(action, user_id=user, entity="phase9", entity_id=detail, detail=detail)


def _report_view(conn: object, row: object) -> ReportOut:
    import sqlite3

    if not isinstance(conn, sqlite3.Connection) or not isinstance(row, sqlite3.Row):
        raise EngineError("SYS-002", "laporan")
    stages = conn.execute(
        "SELECT stage FROM report_stages WHERE report_id=? ORDER BY id",
        (int(row["id"]),),
    ).fetchall()
    return ReportOut(
        id=int(row["id"]),
        number=str(row["number"]),
        mission_id=str(row["mission_id"]),
        revision=int(row["revision"]),
        status=str(row["status"]),
        summary=str(row["summary"]),
        recommendation=str(row["recommendation"]),
        locked=bool(row["locked"]),
        findings=[_finding(item) for item in confirmed_rows(conn)],
        stages=[str(item["stage"]) for item in stages],
    )


def _finding(row: object) -> FindingOut:
    import sqlite3

    if not isinstance(row, sqlite3.Row):
        raise EngineError("SYS-002", "temuan")
    span = row["span_m"]
    return FindingOut(
        title=str(row["title"]),
        class_name=row["class_name"] if isinstance(row["class_name"], str) else None,
        span_m=None if span is None else float(span),
    )


def _package(row: object) -> PackageOut:
    import sqlite3

    if not isinstance(row, sqlite3.Row):
        raise EngineError("SYS-002", "paket")
    return PackageOut(
        id=str(row["id"]),
        name=str(row["name"]),
        created_at=str(row["created_at"]),
        manifest_sha=str(row["manifest_sha"]),
        upload=str(row["upload"]),
        snapshot_count=int(row["snapshot_count"]),
        report_count=int(row["report_count"]),
        bytes=int(row["bytes"]),
    )


def _metrics(settings: object, config_dir: Path) -> list[MetricOut]:
    from ..core.config import Settings

    if not isinstance(settings, Settings):
        return []
    entry = settings.models.entries.get("hydrodetect")
    if entry is None or not entry.metadata:
        return []
    path = config_dir.parent / settings.app.models.dir / entry.metadata
    if not path.is_file():
        return []
    loaded = json.loads(path.read_text(encoding="utf-8"))
    rows = loaded.get("metrics") if isinstance(loaded, dict) else None
    if not isinstance(rows, list):
        return []
    return [_metric(item) for item in rows if isinstance(item, dict)]


def _metric(item: dict[str, object]) -> MetricOut:
    return MetricOut(
        class_name=str(item.get("class_name", "")),
        precision=_num(item.get("precision")),
        recall=_num(item.get("recall")),
        map50=_num(item.get("map50")),
    )


def _num(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)
