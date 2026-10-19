"""Kamera Windows memakai DirectShow. Berkas unggahan ditolak bila bukan video."""

from __future__ import annotations

from fastapi.testclient import TestClient

from deepinsight_engine.diagnostics import camera_state_for
from deepinsight_engine.video import file_source


def test_camera_state_for_open_sources() -> None:
    assert camera_state_for(None) == "not_configured"
    assert camera_state_for("not_configured") == "not_configured"
    assert camera_state_for("connecting") == "connected"
    assert camera_state_for("live") == "connected"
    assert camera_state_for("lost") == "connected"


def test_windows_camera_uses_directshow(monkeypatch) -> None:
    opened: list[tuple[object, object | None]] = []

    class Capture:
        def isOpened(self) -> bool:
            return True

        def set(self, _prop: object, _value: object) -> bool:
            return True

    class FakeCv:
        CAP_DSHOW = 700

        def VideoCapture(self, target: object, api: object | None = None) -> Capture:
            opened.append((target, api))
            return Capture()

    monkeypatch.setattr(file_source, "_cv2", lambda: FakeCv())
    monkeypatch.setattr(file_source.sys, "platform", "win32")
    file_source.open_live("camera", device_index=0)
    assert opened == [(0, 700)]


def test_opened_camera_is_connected_before_the_first_frame(client: TestClient, monkeypatch) -> None:
    class Capture:
        def read(self) -> tuple[bool, None]:
            return False, None

        def release(self) -> None:
            return None

        def isOpened(self) -> bool:
            return True

    monkeypatch.setattr("deepinsight_engine.runtime.open_live", lambda *_a, **_k: Capture())
    opened = client.post("/video/device", json={"kind": "camera", "device_index": 0})
    assert opened.status_code == 200
    assert opened.json()["state"] == "connecting"
    report = client.get("/diagnostics").json()
    assert report["camera_state"] == "connected"
    assert report["video"]["state"] == "connecting"


def test_upload_rejects_a_text_file(client: TestClient) -> None:
    response = client.post(
        "/video/upload",
        files={"file": ("catatan.txt", b"bukan video", "text/plain")},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "API-002"
