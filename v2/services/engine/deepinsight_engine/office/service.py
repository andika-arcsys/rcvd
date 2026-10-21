"""Masuk, audit, dan misi. Ambang dan PIN tidak dihitung di sini."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NoReturn, cast

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from deepinsight_engine.core.config import Settings, UserAccount
from deepinsight_engine.core.errors import EngineError
from deepinsight_engine.core.ids import mission_id
from deepinsight_engine.measure import (
    calibrate,
    critical_limit,
    length,
    limits_from_thresholds,
    rod_test,
)
from deepinsight_engine.measure.compare import geq

from .db import Database
from .findings import insert_candidate, list_candidates
from .models import (
    DashboardView,
    FindingView,
    LoginResult,
    MissionInput,
    MissionView,
    PipelineView,
    RemeasureTask,
    ReviewBanner,
    RodInput,
    RodView,
)

TEAM_ROLES = (
    "ketua_tim",
    "pilot_drone",
    "ahli_ukur",
    "pengelola_data",
    "teknisi_program",
    "pemeriksa_teknik",
)
_HASHER = PasswordHasher()


def _pin_ok(pin_hash: str, pin: str) -> bool:
    try:
        return bool(_HASHER.verify(pin_hash, pin))
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


class Office:
    def __init__(
        self, data_dir: Path, config_dir: Path, settings: Settings, session_id: str
    ) -> None:
        self.data_dir = data_dir
        self.config_dir = config_dir
        self.settings = settings
        self.session_id = session_id
        self.db = Database(data_dir / "deepinsight.db")
        self._user_id: str | None = None

    @property
    def user_id(self) -> str | None:
        return self._user_id

    def audit(
        self, action: str, *, user_id: str | None, entity: str, entity_id: str, detail: str
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self.db.connect() as conn:
            prev = conn.execute("SELECT row_hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
            prev_hash = "" if prev is None else str(prev["row_hash"])
            raw = "|".join([prev_hash, now, action, user_id or "", entity, entity_id, detail])
            row_hash = hashlib.sha256(raw.encode()).hexdigest()
            conn.execute(
                """INSERT INTO audit
                   (ts, user_id, session_id, action, entity, entity_id, detail, prev_hash, row_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    now,
                    user_id,
                    self.session_id,
                    action,
                    entity,
                    entity_id,
                    detail,
                    prev_hash,
                    row_hash,
                ),
            )

    def login(self, user_id: str, pin: str) -> LoginResult:
        state = self._auth_row(user_id)
        locked = _still_locked(state)
        if locked:
            self.audit(
                "login_locked",
                user_id=user_id,
                entity="user",
                entity_id=user_id,
                detail="terkunci",
            )
            raise EngineError("AUTH-002")
        account = next((item for item in self.settings.users.users if item.id == user_id), None)
        if account is None:
            account = self.local_account(user_id)
        if account is None or not _pin_ok(account.pin_hash, pin):
            self._fail_login(user_id)
        self._clear_attempts(user_id)
        self._user_id = account.id
        self.audit(
            "login_ok",
            user_id=account.id,
            entity="user",
            entity_id=account.id,
            detail="masuk",
        )
        return LoginResult(user_id=account.id, name=account.name, roles=list(account.roles))

    def local_account(self, user_id: str) -> UserAccount | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM local_users WHERE id=?", (user_id,)).fetchone()
        if row is None:
            return None
        loaded = json.loads(str(row["roles_json"]))
        roles = [str(item) for item in loaded] if isinstance(loaded, list) else []
        return UserAccount(
            id=str(row["id"]),
            name=str(row["name"]),
            pin_hash=str(row["pin_hash"]),
            roles=roles,
        )

    def pipelines(self) -> list[PipelineView]:
        limits = limits_from_thresholds(self.settings.thresholds)
        return [
            PipelineView(
                id=item.id,
                name=item.name,
                diameter=item.diameter,
                critical_limit_m=critical_limit(item.diameter, limits),
            )
            for item in self.settings.pipelines.pipelines
        ]

    def cameras(self) -> list[str]:
        from ..core.camera_file import camera_ids

        return camera_ids(self.config_dir / "cameras")

    def current(self) -> MissionView | None:
        with self.db.connect() as conn:
            row = _current_row(conn)
            if row is None:
                return None
            return self._view(conn, row)

    def save_draft(self, body: MissionInput) -> MissionView:
        pipe = next(
            (item for item in self.settings.pipelines.pipelines if item.id == body.pipeline_id),
            None,
        )
        location = body.location.strip()
        survey_date = body.survey_date.strip()
        if pipe is None or not _team_ok(body.team) or not location or not survey_date:
            raise EngineError("MIS-001")
        limits = limits_from_thresholds(self.settings.thresholds)
        limit_m = critical_limit(pipe.diameter, limits)
        with self.db.connect() as conn:
            row = _current_row(conn)
            if row is not None and str(row["status"]) != "Direncanakan":
                raise EngineError("MIS-001")
            if row is None:
                serial = int(conn.execute("SELECT COUNT(*) AS n FROM missions").fetchone()["n"]) + 1
                mid = mission_id(datetime.now(UTC), serial)
                conn.execute(
                    """INSERT INTO missions
                       (id, name, location, survey_date, pipeline_id, diameter, critical_limit_m,
                        team_json, status, camera_id, preset_locked, laser_on, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Direncanakan', ?, 0, 0, ?)""",
                    (
                        mid,
                        pipe.name,
                        location,
                        survey_date,
                        pipe.id,
                        pipe.diameter,
                        limit_m,
                        json.dumps(body.team),
                        body.camera_id,
                        datetime.now(UTC).isoformat(),
                    ),
                )
            else:
                conn.execute(
                    """UPDATE missions SET name=?, location=?, survey_date=?, pipeline_id=?,
                       diameter=?, critical_limit_m=?, team_json=?, camera_id=? WHERE id=?""",
                    (
                        pipe.name,
                        location,
                        survey_date,
                        pipe.id,
                        pipe.diameter,
                        limit_m,
                        json.dumps(body.team),
                        body.camera_id,
                        row["id"],
                    ),
                )
            saved = _current_row(conn)
            assert saved is not None
            return self._view(conn, saved)

    def acknowledge(self, preset_locked: bool, laser_on: bool) -> MissionView:
        with self.db.connect() as conn:
            row = _require_draft(conn)
            conn.execute(
                "UPDATE missions SET preset_locked=?, laser_on=? WHERE id=?",
                (int(preset_locked), int(laser_on), row["id"]),
            )
            updated = _current_row(conn)
            assert updated is not None
            return self._view(conn, updated)

    def record_rod(self, body: RodInput) -> RodView:
        ref_cm = self.settings.thresholds.laser.ref_cm
        if ref_cm is None:
            raise EngineError("LASER-001")
        limits = limits_from_thresholds(self.settings.thresholds)
        click = self.settings.thresholds.calibration.click_sigma_px
        cal = calibrate(body.cal_p1, body.cal_p2, ref_cm / 100.0, click, limits, None)
        measured = length(body.meas_p1, body.meas_p2, cal, limits)
        gate = rod_test(measured.meters, limits)
        with self.db.connect() as conn:
            mission = str(_require_draft(conn)["id"])
            conn.execute(
                """INSERT INTO rod_tests
                   (mission_id, session_id, time_of_day, frame_id, snapshot_id, measured_m,
                    error_pct, passed, calibration_status, baseline_hint, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    mission,
                    self.session_id,
                    body.time_of_day,
                    body.frame_id,
                    body.snapshot_id,
                    measured.meters,
                    gate.error_pct,
                    int(gate.passed),
                    cal.status,
                    cal.baseline_hint,
                    datetime.now(UTC).isoformat(),
                ),
            )
        self.audit(
            "rod_test",
            user_id=self._user_id,
            entity="mission",
            entity_id=mission,
            detail=f"passed={gate.passed};error_pct={gate.error_pct}",
        )
        return RodView(
            measured_m=measured.meters,
            error_pct=gate.error_pct,
            passed=gate.passed,
            calibration_status=cal.status,
            baseline_hint=cal.baseline_hint,
            frame_id=body.frame_id,
            snapshot_id=body.snapshot_id,
        )

    def start(self) -> MissionView:
        with self.db.connect() as conn:
            row = _require_draft(conn)
            view = self._view(conn, row)
            if not view.ready:
                raise EngineError("MIS-001")
            snapshot = json.dumps(self.settings.thresholds.model_dump())
            conn.execute(
                """UPDATE missions SET status='Berjalan', thresholds_json=?,
                   started_at=? WHERE id=?""",
                (snapshot, datetime.now(UTC).isoformat(), row["id"]),
            )
            updated = _current_row(conn)
            assert updated is not None
            started = self._view(conn, updated)
        self.audit(
            "mission_started",
            user_id=self._user_id,
            entity="mission",
            entity_id=started.id,
            detail=started.diameter,
        )
        return started

    def dashboard(self) -> DashboardView:
        limits = limits_from_thresholds(self.settings.thresholds)
        with self.db.connect() as conn:
            stored = conn.execute("SELECT * FROM missions ORDER BY created_at").fetchall()
            missions = [_view_of(self, conn, row) for row in stored]
            active = conn.execute(
                "SELECT COUNT(*) AS n FROM missions WHERE status='Berjalan'"
            ).fetchone()
            pending = conn.execute(
                "SELECT COUNT(*) AS n FROM review_items WHERE decided=0"
            ).fetchone()
            spans = conn.execute(
                "SELECT MAX(span_m) AS m FROM review_items WHERE span_m IS NOT NULL"
            ).fetchone()
            running = conn.execute(
                """SELECT critical_limit_m FROM missions WHERE status='Berjalan'
                   ORDER BY started_at DESC LIMIT 1"""
            ).fetchone()
            banner = _banner(conn, limits.warning_ratio, limits.boundary_tol)
            tasks = [
                RemeasureTask(segment=str(item["segment"]), note=str(item["note"]))
                for item in conn.execute("SELECT segment, note FROM remeasure WHERE open=1")
            ]
        assert active is not None and pending is not None and spans is not None
        return DashboardView(
            active_missions=int(active["n"]),
            pending_review=int(pending["n"]),
            snapshots_today=0,
            longest_span_m=None if spans["m"] is None else float(spans["m"]),
            critical_limit_m=None if running is None else float(running["critical_limit_m"]),
            banner=banner,
            missions=missions,
            remeasure=tasks,
        )

    def add_finding(
        self,
        frame_id: str,
        jpeg_path: str,
        class_name: str | None = None,
        score: float | None = None,
    ) -> int:
        row_id = insert_candidate(self.db, self.session_id, frame_id, jpeg_path, class_name, score)
        detail = jpeg_path if not class_name else f"{jpeg_path}|{class_name}"
        self.audit(
            "mark_finding",
            user_id=self._user_id,
            entity="finding",
            entity_id=frame_id,
            detail=detail,
        )
        return row_id

    def findings(self) -> list[FindingView]:
        return list_candidates(self.db)

    def add_review_item(
        self, kind: str, title: str, span_m: float | None, limit_m: float | None
    ) -> None:
        with self.db.connect() as conn:
            conn.execute(
                """INSERT INTO review_items (kind, title, span_m, limit_m, decided)
                   VALUES (?, ?, ?, ?, 0)""",
                (kind, title, span_m, limit_m),
            )

    def add_remeasure(self, segment: str, note: str) -> None:
        with self.db.connect() as conn:
            conn.execute(
                "INSERT INTO remeasure (segment, note, open) VALUES (?, ?, 1)",
                (segment, note),
            )

    def _view(self, conn: sqlite3.Connection, row: sqlite3.Row) -> MissionView:
        return _mission_view(self, conn, row)

    def _auth_row(self, user_id: str) -> sqlite3.Row | None:
        with self.db.connect() as conn:
            found = conn.execute("SELECT * FROM auth_state WHERE user_id=?", (user_id,)).fetchone()
            return cast(sqlite3.Row | None, found)

    def _fail_login(self, user_id: str) -> NoReturn:
        auth = self.settings.thresholds.auth
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM auth_state WHERE user_id=?", (user_id,)).fetchone()
            attempts = 0 if row is None else int(row["attempts"])
            attempts += 1
            locked_until = None
            action = "login_failed"
            if attempts >= auth.max_attempts:
                until = datetime.now(UTC) + timedelta(minutes=auth.lock_minutes)
                locked_until = until.isoformat()
                attempts = 0
                action = "login_locked"
            if row is None:
                conn.execute(
                    "INSERT INTO auth_state (user_id, attempts, locked_until) VALUES (?, ?, ?)",
                    (user_id, attempts, locked_until),
                )
            else:
                conn.execute(
                    "UPDATE auth_state SET attempts=?, locked_until=? WHERE user_id=?",
                    (attempts, locked_until, user_id),
                )
        self.audit(action, user_id=user_id, entity="user", entity_id=user_id, detail=action)
        raise EngineError("AUTH-002" if action == "login_locked" else "AUTH-001")

    def _clear_attempts(self, user_id: str) -> None:
        with self.db.connect() as conn:
            conn.execute(
                "INSERT INTO auth_state (user_id, attempts, locked_until) VALUES (?, 0, NULL) "
                "ON CONFLICT(user_id) DO UPDATE SET attempts=0, locked_until=NULL",
                (user_id,),
            )


def _still_locked(state: sqlite3.Row | None) -> bool:
    if state is None or state["locked_until"] is None:
        return False
    return datetime.fromisoformat(str(state["locked_until"])) > datetime.now(UTC)


def _team_ok(team: dict[str, str]) -> bool:
    return all(team.get(role, "").strip() for role in TEAM_ROLES)


def _current_row(conn: sqlite3.Connection) -> sqlite3.Row | None:
    found = conn.execute(
        """SELECT * FROM missions WHERE status IN ('Direncanakan', 'Berjalan')
           ORDER BY CASE status WHEN 'Berjalan' THEN 0 ELSE 1 END, created_at DESC LIMIT 1"""
    ).fetchone()
    return cast(sqlite3.Row | None, found)


def _require_draft(conn: sqlite3.Connection) -> sqlite3.Row:
    row = _current_row(conn)
    if row is None or str(row["status"]) != "Direncanakan":
        raise EngineError("MIS-001")
    return row


def _latest_rod(conn: sqlite3.Connection, mission_id_value: str) -> sqlite3.Row | None:
    found = conn.execute(
        "SELECT * FROM rod_tests WHERE mission_id=? ORDER BY id DESC LIMIT 1",
        (mission_id_value,),
    ).fetchone()
    return cast(sqlite3.Row | None, found)


def _mission_view(office: Office, conn: sqlite3.Connection, row: sqlite3.Row) -> MissionView:
    rod_row = _latest_rod(conn, str(row["id"]))
    team = json.loads(str(row["team_json"]))
    camera_id = None if row["camera_id"] is None else str(row["camera_id"])
    lens = bool(camera_id) and (office.config_dir / "cameras" / f"{camera_id}.yaml").is_file()
    disk_ok = shutil.disk_usage(office.data_dir).free > 0
    rod = None if rod_row is None else _rod_view(rod_row)
    precheck = {
        "rod": rod is not None and rod.passed,
        "lens": lens,
        "preset_locked": bool(row["preset_locked"]),
        "laser_on": bool(row["laser_on"]),
        "disk": disk_ok,
    }
    ready = all(precheck.values()) and _team_ok(team) and bool(str(row["location"]).strip())
    return MissionView(
        id=str(row["id"]),
        name=str(row["name"]),
        location=str(row["location"]),
        survey_date=str(row["survey_date"]),
        pipeline_id=str(row["pipeline_id"]),
        diameter=str(row["diameter"]),
        critical_limit_m=float(row["critical_limit_m"]),
        team=team,
        status=str(row["status"]),
        camera_id=camera_id,
        preset_locked=bool(row["preset_locked"]),
        laser_on=bool(row["laser_on"]),
        rod=rod,
        precheck=precheck,
        ready=ready,
        laser_ref_cm=office.settings.thresholds.laser.ref_cm,
    )


def _view_of(office: Office, conn: sqlite3.Connection, row: sqlite3.Row) -> MissionView:
    return _mission_view(office, conn, row)


def _rod_view(row: sqlite3.Row) -> RodView:
    return RodView(
        measured_m=float(row["measured_m"]),
        error_pct=float(row["error_pct"]),
        passed=bool(row["passed"]),
        calibration_status=str(row["calibration_status"]),
        baseline_hint=None if row["baseline_hint"] is None else str(row["baseline_hint"]),
        frame_id=str(row["frame_id"]),
        snapshot_id=str(row["snapshot_id"]),
    )


def _banner(conn: sqlite3.Connection, warning_ratio: float, tol: float) -> ReviewBanner | None:
    rows = conn.execute("SELECT * FROM review_items WHERE decided=0").fetchall()
    for row in rows:
        span = None if row["span_m"] is None else float(row["span_m"])
        limit = None if row["limit_m"] is None else float(row["limit_m"])
        leakage = str(row["kind"]) == "leakage"
        near = span is not None and limit is not None and geq(span, warning_ratio * limit, tol)
        if leakage or near:
            return ReviewBanner(title=str(row["title"]), kind=str(row["kind"]))
    return None
