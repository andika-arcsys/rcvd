"""Kamera Windows memakai DirectShow. Berkas unggahan ditolak bila bukan video."""

from __future__ import annotations

from fastapi.testclient import TestClient

from deepinsight_engine.video import file_source


def test_windows_camera_uses_directshow(monkeypatch) -> None:
    opened: list[tuple[object, object | None]] = []

    class Capture:
        def isOpened(self) -> bool:
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


def test_upload_rejects_a_text_file(client: TestClient) -> None:
    response = client.post(
        "/video/upload",
        files={"file": ("catatan.txt", b"bukan video", "text/plain")},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "API-002"
