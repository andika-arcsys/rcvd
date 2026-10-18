"""Simpan snapshot menghitung ulang, menolak tepi, dan tidak menimpa berkas."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient

from deepinsight_engine.core.config import load_settings
from deepinsight_engine.core.errors import EngineError
from deepinsight_engine.measure.edge import edge_risk
from deepinsight_engine.measure.laser import detect_laser
from deepinsight_engine.measure.persist import write_new

REPO = Path(__file__).resolve().parents[3] / "config"


def _paint(path: Path, image: np.ndarray) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    assert cv2.imwrite(str(path), image)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    side = {"sha256": digest, "path": str(path), "aquaclear_preset": "light"}
    path.with_suffix(".json").write_text(json.dumps(side), encoding="utf-8")
    return digest


def _gray(width: int, height: int) -> np.ndarray:
    return np.full((height, width, 3), 40, np.uint8)


def _save(client: TestClient, frame_id: str):
    length = [{"a": {"x": 0, "y": 0}, "b": {"x": 300, "y": 400}}]
    return client.post(
        "/snapshots",
        json={
            "frame_id": frame_id,
            "ref_cm": 10,
            "calibration": {"a": {"x": 0, "y": 0}, "b": {"x": 100, "y": 0}},
            "lengths": length,
            "areas": [],
            "annotations": [],
            "marker": "P0",
            "note": "",
        },
    )


def test_two_red_blobs_and_one_blob() -> None:
    cfg = load_settings(REPO).thresholds.laser
    image = np.zeros((64, 64, 3), np.uint8)
    cv2.rectangle(image, (8, 8), (20, 20), (0, 0, 255), -1)
    cv2.rectangle(image, (40, 24), (56, 40), (0, 0, 255), -1)
    assert len(detect_laser(image.tobytes(), 64, 64, cfg)) == 2
    single = np.zeros((64, 64, 3), np.uint8)
    cv2.rectangle(single, (8, 8), (20, 20), (0, 0, 255), -1)
    assert len(detect_laser(single.tobytes(), 64, 64, cfg)) == 1


def test_edge_risk_follows_canny() -> None:
    cal = load_settings(REPO).thresholds.calibration
    image = np.zeros((64, 64, 3), np.uint8)
    image[:, 30] = 255
    flags = edge_risk(
        image.tobytes(),
        64,
        64,
        [(30, 32), (8, 32)],
        cal.canny_low,
        cal.canny_high,
        cal.edge_risk_px,
    )
    assert flags == [True, False]


def test_save_recomputes_and_versions(client: TestClient, tmp_path: Path) -> None:
    path = tmp_path / "evidence" / "frm-ukur.png"
    digest = _paint(path, _gray(420, 420))
    first = _save(client, "frm-ukur")
    assert first.status_code == 200
    body = first.json()
    assert body["calibration"]["status"] == "ESTIMATE_ONLY"
    assert body["calibration"]["camera_present"] is False
    assert body["measurements"][0]["meters"] == 0.5
    assert body["version"] == 1
    assert body["supersedes"] is None
    assert body["freeze_no"] == 1
    assert body["marker"] == "P0"
    assert body["aquaclear_preset"] == "light"
    assert "150" in (body["calibration"]["baseline_hint"] or "")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    second = _save(client, "frm-ukur")
    assert second.status_code == 200
    again = second.json()
    assert again["id"] != body["id"]
    assert again["version"] == 2
    assert again["supersedes"] == body["id"]
    assert again["freeze_no"] == 2
    snaps = list((tmp_path / "snapshots").glob("*.json"))
    assert len(snaps) == 2
    assert (tmp_path / "snapshots" / f"{body['id']}.jpg").is_file()


def test_uncalibrated_and_edge_are_rejected(client: TestClient, tmp_path: Path) -> None:
    _paint(tmp_path / "evidence" / "frm-tolak.png", _gray(80, 80))
    short = client.post(
        "/snapshots",
        json={
            "frame_id": "frm-tolak",
            "ref_cm": 10,
            "calibration": {"a": {"x": 0, "y": 0}, "b": {"x": 10, "y": 0}},
            "lengths": [],
            "areas": [],
            "annotations": [],
            "note": "",
        },
    )
    assert short.status_code == 422
    assert short.json()["code"] == "SNAP-001"
    assert list((tmp_path / "snapshots").glob("*.json")) == []
    image = np.zeros((64, 64, 3), np.uint8)
    image[:, 30] = 255
    _paint(tmp_path / "evidence" / "frm-tepi.png", image)
    response = client.post(
        "/snapshots",
        json={
            "frame_id": "frm-tepi",
            "ref_cm": 10,
            "calibration": {"a": {"x": 0, "y": 0}, "b": {"x": 100, "y": 0}},
            "lengths": [{"a": {"x": 30, "y": 32}, "b": {"x": 50, "y": 32}}],
            "areas": [],
            "annotations": [],
            "note": "",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "EDGE-001"


def test_frozen_detail_uses_evidence_pixels(client: TestClient, tmp_path: Path) -> None:
    wide = np.full((1500, 3000, 3), 90, np.uint8)
    _paint(tmp_path / "evidence" / "frm-res.png", wide)
    display = client.get("/measure/context/frm-res")
    high = client.get("/measure/context/frm-res", params={"detail": "high"})
    native = client.get("/measure/context/frm-res", params={"detail": "native"})
    assert display.status_code == 200
    assert (display.json()["shown_width"], display.json()["shown_height"]) == (1280, 640)
    assert display.json()["detail"] == "display"
    assert (high.json()["shown_width"], high.json()["shown_height"]) == (2560, 1280)
    assert (native.json()["shown_width"], native.json()["shown_height"]) == (3000, 1500)
    assert _jpeg_size(display.json()["jpeg_b64"]) == (1280, 640)
    assert _jpeg_size(native.json()["jpeg_b64"]) == (3000, 1500)
    assert native.json()["width"] == 3000
    _paint(tmp_path / "evidence" / "frm-kecil.png", np.full((60, 80, 3), 20, np.uint8))
    full = client.get("/measure/context/frm-kecil", params={"detail": "native"})
    assert _jpeg_size(full.json()["jpeg_b64"]) == (80, 60)


def _jpeg_size(payload: str) -> tuple[int, int]:
    image = cv2.imdecode(np.frombuffer(base64.b64decode(payload), np.uint8), cv2.IMREAD_COLOR)
    assert image is not None
    height, width = image.shape[:2]
    return width, height


def test_write_new_refuses_existing_name(tmp_path: Path) -> None:
    body: dict[str, object] = {"id": "SNP-SES-20261017-0000-0001"}
    write_new(tmp_path, body, b"jpeg")
    try:
        write_new(tmp_path, body, b"jpeg")
    except EngineError as exc:
        assert exc.spec.code == "SYS-002"
    else:
        raise AssertionError("berkas lama tertimpa")
