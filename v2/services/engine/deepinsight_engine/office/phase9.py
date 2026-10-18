"""Laporan, paket bukti, dan perubahan pengaturan. Keputusan tidak dihapus."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from deepinsight_engine.core.config import Settings, Thresholds
from deepinsight_engine.core.errors import EngineError

ADMIN = {"ketua_tim", "teknisi_program"}
_NEXT = {"draft": ("reviewed", "pemeriksa_teknik"), "reviewed": ("approved", "ketua_tim")}


def build_report(conn: sqlite3.Connection, mission_id: str, user_id: str, role: str) -> int:
    revision = _next_revision(conn, mission_id)
    number = f"RPT-{mission_id}-R{revision}"
    now = _now()
    cursor = conn.execute(
        """INSERT INTO reports
           (number, mission_id, revision, status, summary, recommendation,
            locked, supersedes, created_at)
           VALUES (?, ?, ?, 'draft', ?, '', 0, NULL, ?)""",
        (number, mission_id, revision, _summary(conn), now),
    )
    report_id = int(cursor.lastrowid or 0)
    _stage(conn, report_id, "draft", user_id, role, now)
    return report_id


def update_report(
    conn: sqlite3.Connection, report_id: int, summary: str, recommendation: str
) -> None:
    row = _report(conn, report_id)
    if int(row["locked"]):
        raise EngineError("RPT-002", str(report_id))
    conn.execute(
        "UPDATE reports SET summary=?, recommendation=? WHERE id=?",
        (summary, recommendation, report_id),
    )


def advance_report(
    conn: sqlite3.Connection,
    report_id: int,
    user_id: str,
    role: str,
    roles_of: dict[str, list[str]],
) -> str:
    row = _report(conn, report_id)
    if int(row["locked"]):
        raise EngineError("RPT-002", str(report_id))
    status = str(row["status"])
    pair = _NEXT.get(status)
    if pair is None or role != pair[1] or role not in roles_of.get(user_id, []):
        raise EngineError("API-002", role)
    last = _last_stage(conn, report_id)
    if last is not None and str(last["user_id"]) == user_id:
        raise EngineError("RPT-001", user_id)
    nxt, _expected = pair
    locked = 1 if nxt == "approved" else 0
    conn.execute(
        "UPDATE reports SET status=?, locked=? WHERE id=?",
        (nxt, locked, report_id),
    )
    _stage(conn, report_id, nxt, user_id, role, _now())
    return nxt


def revise_report(conn: sqlite3.Connection, report_id: int, user_id: str, role: str) -> int:
    row = _report(conn, report_id)
    mission = str(row["mission_id"])
    revision = _next_revision(conn, mission)
    number = f"RPT-{mission}-R{revision}"
    now = _now()
    cursor = conn.execute(
        """INSERT INTO reports
           (number, mission_id, revision, status, summary, recommendation,
            locked, supersedes, created_at)
           VALUES (?, ?, ?, 'draft', ?, ?, 0, ?, ?)""",
        (number, mission, revision, row["summary"], row["recommendation"], report_id, now),
    )
    new_id = int(cursor.lastrowid or 0)
    _stage(conn, new_id, "draft", user_id, role, now)
    return new_id


def confirmed_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            "SELECT * FROM review_items WHERE queue_status='confirmed' ORDER BY id"
        ).fetchall()
    )


def seal_package(
    conn: sqlite3.Connection,
    data_dir: Path,
    session_id: str,
    upload_dir: str | None,
) -> sqlite3.Row:
    package_id = f"PKG-{session_id}"
    existing = conn.execute("SELECT * FROM packages WHERE id=?", (package_id,)).fetchone()
    if existing is not None:
        return _row(existing, package_id)
    root = data_dir / "packages" / package_id
    root.mkdir(parents=True, exist_ok=True)
    files = _copy_snapshots(data_dir / "snapshots", root)
    digest = _bundle_sha(files)
    manifest = {"files": files, "package_sha256": digest}
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    upload = _copy_upload(root, upload_dir)
    size = sum(path.stat().st_size for path in root.rglob("*") if path.is_file())
    reports = conn.execute("SELECT COUNT(*) AS n FROM reports").fetchone()
    report_count = int(reports["n"]) if reports else 0
    conn.execute(
        """INSERT INTO packages
           (id, name, created_at, manifest_sha, upload, path, snapshot_count, report_count, bytes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            package_id,
            session_id,
            _now(),
            digest,
            upload,
            str(root),
            len(files),
            report_count,
            size,
        ),
    )
    stored = conn.execute("SELECT * FROM packages WHERE id=?", (package_id,)).fetchone()
    return _row(stored, package_id)


def verify_package(conn: sqlite3.Connection, package_id: str) -> str:
    row = conn.execute("SELECT * FROM packages WHERE id=?", (package_id,)).fetchone()
    if row is None:
        raise EngineError("API-003", package_id)
    root = Path(str(row["path"]))
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    files = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(files, list):
        return "recheck"
    checked: list[dict[str, str]] = []
    for item in files:
        if not isinstance(item, dict):
            return "recheck"
        name = str(item.get("name", ""))
        expect = str(item.get("sha256", ""))
        path = root / name
        if not path.is_file() or _sha_file(path) != expect:
            return "recheck"
        checked.append({"name": name, "sha256": expect})
    recorded = str(manifest.get("package_sha256", "")) if isinstance(manifest, dict) else ""
    if _bundle_sha(checked) != recorded or recorded != str(row["manifest_sha"]):
        return "recheck"
    return "intact"


def list_packages(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM packages ORDER BY created_at").fetchall())


def patch_setting(
    conn: sqlite3.Connection,
    settings: Settings,
    user_id: str,
    role: str,
    roles_of: dict[str, list[str]],
    key: str,
    value: str,
) -> tuple[Settings, str | None]:
    if role not in ADMIN or role not in roles_of.get(user_id, []):
        raise EngineError("SET-001", role)
    if key not in {"laser.ref_cm", "upload_dir", "models_dir"}:
        raise EngineError("API-002", key)
    previous = _override(conn, key)
    conn.execute(
        "INSERT INTO settings_override (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    updated = apply_override(settings, key, previous, value)
    return updated, previous


def apply_override(settings: Settings, key: str, previous: str | None, value: str) -> Settings:
    del previous
    if key == "models_dir":
        if not value.strip():
            raise EngineError("API-002", key)
        models = settings.app.models.model_copy(update={"dir": value.strip()})
        app = settings.app.model_copy(update={"models": models})
        return settings.model_copy(update={"app": app})
    if key != "laser.ref_cm":
        return settings
    if value in {"", "null"}:
        ref = None
    else:
        try:
            ref = float(value)
        except ValueError as exc:
            raise EngineError("API-002", "laser.ref_cm") from exc
    laser = settings.thresholds.laser.model_copy(update={"ref_cm": ref})
    thresholds: Thresholds = settings.thresholds.model_copy(update={"laser": laser})
    return settings.model_copy(update={"thresholds": thresholds})


def override_value(conn: sqlite3.Connection, key: str) -> str | None:
    return _override(conn, key)


def add_local_user(
    conn: sqlite3.Connection,
    user_id: str,
    name: str,
    pin_hash: str,
    roles: list[str],
    actor: str,
    role: str,
    roles_of: dict[str, list[str]],
) -> None:
    if role not in ADMIN or role not in roles_of.get(actor, []):
        raise EngineError("SET-001", role)
    conn.execute(
        "INSERT INTO local_users (id, name, pin_hash, roles_json) VALUES (?, ?, ?, ?)",
        (user_id, name, pin_hash, json.dumps(roles)),
    )


def queue_retrain(conn: sqlite3.Connection, user_id: str) -> int:
    cursor = conn.execute(
        "INSERT INTO retrain_requests (user_id, created_at) VALUES (?, ?)",
        (user_id, _now()),
    )
    return int(cursor.lastrowid or 0)


def release_model(
    conn: sqlite3.Connection,
    user_id: str,
    role: str,
    roles_of: dict[str, list[str]],
    name: str,
    version: str,
) -> int:
    if role != "teknisi_program" or role not in roles_of.get(user_id, []):
        raise EngineError("SET-001", role)
    cursor = conn.execute(
        """INSERT INTO model_releases (name, version, user_id, created_at)
           VALUES (?, ?, ?, ?)""",
        (name, version, user_id, _now()),
    )
    return int(cursor.lastrowid or 0)


def training_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM review_items WHERE training=1").fetchone()
    return int(row["n"]) if row else 0


def pdf_bytes(lines: list[str]) -> bytes:
    commands = ["BT", "/F1 11 Tf", "50 780 Td"]
    for index, line in enumerate(lines[:40]):
        if index:
            commands.append("0 -16 Td")
        commands.append(f"({_pdf_escape(line)}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1", errors="replace")
    return _wrap_pdf(stream)


def _summary(conn: sqlite3.Connection) -> str:
    count = len(confirmed_rows(conn))
    return f"Disusun dari {count} temuan terkonfirmasi."


def _report(conn: sqlite3.Connection, report_id: int) -> sqlite3.Row:
    found = conn.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    if found is None:
        raise EngineError("API-003", str(report_id))
    return _row(found, str(report_id))


def _last_stage(conn: sqlite3.Connection, report_id: int) -> sqlite3.Row | None:
    found = conn.execute(
        "SELECT * FROM report_stages WHERE report_id=? ORDER BY id DESC LIMIT 1",
        (report_id,),
    ).fetchone()
    if found is None:
        return None
    return _row(found, str(report_id))


def _stage(
    conn: sqlite3.Connection, report_id: int, stage: str, user_id: str, role: str, now: str
) -> None:
    conn.execute(
        """INSERT INTO report_stages (report_id, stage, user_id, role, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (report_id, stage, user_id, role, now),
    )


def _next_revision(conn: sqlite3.Connection, mission_id: str) -> int:
    row = conn.execute(
        "SELECT MAX(revision) AS n FROM reports WHERE mission_id=?",
        (mission_id,),
    ).fetchone()
    if row is None or row["n"] is None:
        return 0
    return int(row["n"]) + 1


def _override(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM settings_override WHERE key=?", (key,)).fetchone()
    return None if row is None else str(row["value"])


def _copy_snapshots(source: Path, root: Path) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    if not source.is_dir():
        return files
    for path in sorted(source.glob("*")):
        if not path.is_file():
            continue
        dest = root / path.name
        shutil.copyfile(path, dest)
        files.append({"name": path.name, "sha256": _sha_file(dest)})
    return files


def _copy_upload(root: Path, upload_dir: str | None) -> str:
    if not upload_dir:
        return "pending"
    target = Path(upload_dir) / root.name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(root, target)
    return "copied"


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bundle_sha(files: list[dict[str, str]]) -> str:
    payload = json.dumps(files, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _pdf_escape(line: str) -> str:
    return line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap_pdf(stream: bytes) -> bytes:
    parts = [
        b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n",
        b"2 0 obj<< /Type /Pages /Count 1 /Kids [3 0 R] >>endobj\n",
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n",
        f"4 0 obj<< /Length {len(stream)} >>stream\n".encode() + stream + b"\nendstream\nendobj\n",
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n",
    ]
    body = b"".join(parts)
    header = b"%PDF-1.4\n"
    start = len(header)
    offsets = [start]
    cursor = start
    for part in parts[:-1]:
        cursor += len(part)
        offsets.append(cursor)
    xref_at = start + len(body)
    xref = [f"xref\n0 {len(parts) + 1}\n", "0000000000 65535 f \n"]
    xref.extend(f"{offset:010d} 00000 n \n" for offset in offsets)
    trailer = f"trailer<< /Size {len(parts) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF"
    return header + body + "".join(xref).encode() + trailer.encode()


def _row(found: object, label: str) -> sqlite3.Row:
    if not isinstance(found, sqlite3.Row):
        raise EngineError("SYS-002", label)
    return found


def _now() -> str:
    return datetime.now(UTC).isoformat()
