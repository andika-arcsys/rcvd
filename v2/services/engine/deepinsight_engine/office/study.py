"""Kelengkapan kajian Dashboard. Setiap baris dibaca dari berkas atau basis data.

Kosong tetap kosong. Tidak ada sel prosedur, rumus, atau metrik yang diisi di sini.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from deepinsight_engine.core.camera_file import measured_camera_ids
from deepinsight_engine.core.config import Settings
from deepinsight_engine.video.quality import configured

from .models import StudyItem

_READY = "siap"
_EMPTY = "kosong"


def snapshots_today(folder: Path, moment: datetime | None = None) -> int:
    """Hitung berkas SNAP hari ini. Stempel mengikuti jam konsol, sama seperti nama berkas."""
    if not folder.is_dir():
        return 0
    day = (moment or datetime.now()).strftime("%Y%m%d")
    return sum(1 for path in folder.glob(f"{day}*_SNAP.json") if path.is_file())


def study_items(settings: Settings, config_dir: Path, conn: sqlite3.Connection) -> list[StudyItem]:
    models = (config_dir.parent / settings.app.models.dir).resolve()
    rows = [
        *_evidence(settings, config_dir),
        *_models(settings, models),
        *_reports(config_dir, conn),
        *_procedure(settings),
        *_sustain(settings),
        *_archive(conn),
    ]
    return rows


def _evidence(settings: Settings, config_dir: Path) -> list[StudyItem]:
    source = settings.video.source.kind
    cameras = measured_camera_ids(config_dir / "cameras")
    laser = settings.thresholds.laser.ref_cm
    limits = settings.thresholds.span.critical_limit_m
    names = ", ".join(sorted(settings.aquaclear.presets))
    return [
        _item(
            "D-02",
            "bukti",
            "Bukti",
            "Sumber video lapangan",
            source is not None,
            source or "Jenis sumber belum diisi",
            "/pengaturan",
        ),
        _item(
            "D-04",
            "bukti",
            "Bukti",
            "File kalibrasi kamera",
            bool(cameras),
            ", ".join(cameras) if cameras else "Belum ada file kamera",
            "/misi",
        ),
        _item(
            "D-05",
            "bukti",
            "Bukti",
            "Jarak dua titik laser",
            laser is not None and laser > 0,
            "Belum diisi" if laser is None else f"{_num(laser)} cm",
            "/pengaturan",
        ),
        _item(
            "D-15",
            "bukti",
            "Bukti",
            "Preset AquaClear",
            bool(settings.aquaclear.presets),
            names or "Preset kosong",
            "/pengaturan",
        ),
        _item(
            "D-21",
            "bukti",
            "Bukti",
            "Batas kritis bentang",
            True,
            f"16 inci {_num(limits.inch_16)} m, 8 inci {_num(limits.inch_8)} m",
            "/gallery/span",
        ),
        _item(
            "D-22",
            "bukti",
            "Bukti",
            "Ambang kekeruhan",
            configured(settings.video.turbidity),
            "Ambang terisi" if configured(settings.video.turbidity) else "Keempat batas kosong",
            "/live",
        ),
    ]


def _models(settings: Settings, root: Path) -> list[StudyItem]:
    hydro = settings.models.entries.get("hydrodetect")
    spatial = settings.models.entries.get("spatialsight")
    weights = _exists(root, None if hydro is None else hydro.weights)
    onnx = _exists(root, None if hydro is None else hydro.onnx)
    classes = _exists(root, None if hydro is None else hydro.classes)
    meta = _exists(root, None if hydro is None else hydro.metadata)
    local = _exists(root, None if spatial is None else spatial.checkpoint) or _exists(
        root, None if spatial is None else spatial.onnx
    )
    sight = settings.spatialsight
    sight_detail = f"{sight.model_id}, proses {sight.process_res}"
    if not local:
        sight_detail = f"{sight_detail}. Berkas lokal tidak ada"
    return [
        _item(
            "D-10",
            "model",
            "Model",
            "Bobot HydroDetect",
            weights or onnx,
            "Berkas bobot ada" if weights or onnx else "model.pt dan model.onnx tidak ada",
            "/analisis-ai",
        ),
        _item(
            "D-11",
            "model",
            "Model",
            "Urutan kelas HydroDetect",
            classes,
            "classes.json ada" if classes else "classes.json tidak ada",
            "/analisis-ai",
        ),
        _item(
            "D-12",
            "model",
            "Model",
            "Metrik resmi model",
            meta,
            "metadata.json ada" if meta else "metadata.json tidak ada",
            "/analisis-ai",
        ),
        _item(
            "D-14",
            "model",
            "Model",
            "Depth Anything 3",
            local,
            sight_detail,
            "/live/spatialsight",
        ),
    ]


def _reports(config_dir: Path, conn: sqlite3.Connection) -> list[StudyItem]:
    approved = _count(conn, "SELECT COUNT(*) AS n FROM reports WHERE status='approved'")
    open_rows = _count(conn, "SELECT COUNT(*) AS n FROM reports WHERE status!='approved'")
    template = list(config_dir.glob("report_template.*"))
    return [
        _item(
            "RPT",
            "laporan",
            "Laporan",
            "Laporan terkunci",
            approved > 0,
            f"{approved} disetujui, {open_rows} belum disetujui",
            "/laporan",
        ),
        _item(
            "D-40",
            "laporan",
            "Laporan",
            "Templat laporan resmi",
            bool(template),
            template[0].name if template else "PDF memakai nomor, ringkasan, dan rekomendasi",
            "/laporan",
        ),
    ]


def _procedure(settings: Settings) -> list[StudyItem]:
    form = settings.procedure
    return [
        _item(
            "D-30",
            "pims",
            "PIMS / RBI",
            "Matriks PR-06-019",
            form.matrix is not None,
            "Tabel warna terisi" if form.matrix is not None else "Tabel matriks kosong",
            "/pims",
        ),
        _item(
            "D-31",
            "pims",
            "PIMS / RBI",
            "PoF geohazard PR-06-111",
            form.pof is not None,
            "Kategori terisi" if form.pof is not None else "Kategori PoF kosong",
            "/pims",
        ),
        _item(
            "D-32",
            "pims",
            "PIMS / RBI",
            "LoIE PR-06-117",
            bool(form.loie),
            "Daftar A–E terisi" if form.loie else "Daftar LoIE kosong",
            "/pims",
        ),
        _item(
            "D-35",
            "pims",
            "PIMS / RBI",
            "Posisi risiko terakhir",
            bool(form.prior_position),
            form.prior_position or "Posisi S kosong",
            "/pims",
        ),
    ]


def _sustain(settings: Settings) -> list[StudyItem]:
    form = settings.sustainability
    ready = bool(form.hours_formula and form.cost_formula and form.emission_formula)
    missing = [
        name
        for name, value in (
            ("jam", form.hours_formula),
            ("biaya", form.cost_formula),
            ("emisi", form.emission_formula),
        )
        if not value
    ]
    detail = "Tiga rumus terisi" if ready else "Kosong: " + ", ".join(missing)
    return [
        _item(
            "D-41",
            "sustain",
            "Sustainability",
            "Rumus jam, biaya, emisi",
            ready,
            detail,
            "/sustainability",
        )
    ]


def _archive(conn: sqlite3.Connection) -> list[StudyItem]:
    upload = conn.execute("SELECT value FROM settings_override WHERE key='upload_dir'").fetchone()
    folder = "" if upload is None else str(upload["value"]).strip()
    pending = _count(conn, "SELECT COUNT(*) AS n FROM packages WHERE upload='pending'")
    copied = _count(conn, "SELECT COUNT(*) AS n FROM packages WHERE upload='copied'")
    total = pending + copied
    if total == 0:
        package_ready = False
        package_detail = "Belum ada paket"
    else:
        package_ready = pending == 0
        package_detail = f"{pending} unggah tertunda, {copied} tersalin"
    return [
        _item(
            "D-43",
            "arsip",
            "Arsip",
            "Lokasi unggah",
            bool(folder),
            folder or "Lokasi unggah kosong",
            "/pengaturan",
        ),
        _item(
            "PKG",
            "arsip",
            "Arsip",
            "Salinan paket bukti",
            package_ready,
            package_detail,
            "/arsip",
        ),
    ]


def _item(
    code: str,
    group: str,
    group_label: str,
    title: str,
    ready: bool,
    detail: str,
    path: str,
) -> StudyItem:
    return StudyItem(
        code=code,
        group=group,
        group_label=group_label,
        title=title,
        state=_READY if ready else _EMPTY,
        detail=detail,
        path=path,
    )


def _exists(root: Path, relative: str | None) -> bool:
    if not relative:
        return False
    return (root / relative).is_file()


def _count(conn: sqlite3.Connection, sql: str) -> int:
    row = conn.execute(sql).fetchone()
    return 0 if row is None else int(row["n"])


def _num(value: float) -> str:
    return f"{value:g}".replace(".", ",")
