from __future__ import annotations

import hashlib
import importlib
import time
from pathlib import Path

from fastapi.testclient import TestClient

from deepinsight_engine.core.video_config import TurbidityCfg
from deepinsight_engine.video.encode import encode_jpeg
from deepinsight_engine.video.frames import StoredFrame
from deepinsight_engine.video.quality import configured, turbidity_level
from deepinsight_engine.video.synthetic import gradient_bgr


def _clip(path: Path) -> None:
    cv2 = importlib.import_module("cv2")
    np = importlib.import_module("numpy")
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (32, 24))
    assert writer.isOpened()
    for index in range(4):
        image = np.zeros((24, 32, 3), dtype="uint8")
        image[:, :, 1] = 40 + index
        writer.write(image)
    writer.release()


def test_file_device_pushes_frames(client: TestClient, tmp_path: Path) -> None:
    path = tmp_path / "klip.avi"
    _clip(path)
    opened = client.post("/video/device", json={"kind": "file", "path": str(path)})
    assert opened.status_code == 200
    status = opened.json()
    for _ in range(40):
        if status["frame_count"] > 0:
            break
        time.sleep(0.05)
        status = client.get("/video/status").json()
    assert status["frame_count"] > 0
    assert status["state"] == "live"
    assert status["recording"] is False
    assert status["turbidity_configured"] is False
    assert status["turbidity_level"] is None


def test_empty_rtsp_is_vid_003(client: TestClient) -> None:
    response = client.post("/video/device", json={"kind": "rtsp"})
    assert response.status_code == 503
    assert response.json()["code"] == "VID-003"
    assert response.json()["detail"] == "rtsp"


def test_lost_signal_rejects_freeze(client: TestClient) -> None:
    frames = client.post("/video/synthetic", json={"count": 1, "width": 32, "height": 24})
    frame_id = frames.json()["frame_ids"][0]
    runtime = client.app.state.runtime
    gap = runtime._settings.thresholds.video.lost_signal_s
    runtime.pipeline.last_at = time.monotonic() - gap - 0.05
    runtime.poll()
    status = client.get("/video/status").json()
    assert status["state"] == "lost"
    assert status["lost"] is True
    frozen = client.post("/freeze", json={"frame_id": frame_id})
    assert frozen.status_code == 503
    assert frozen.json()["code"] == "VID-001"


def test_switch_runs_unload_then_load(client: TestClient) -> None:
    runtime = client.app.state.runtime
    seen: list[str] = []
    release = runtime.models._release
    open_worker = runtime.models._open

    def wrapped_release() -> None:
        seen.append(runtime.models.state)
        release()

    def wrapped_open(name: str, entry: object, preset: str | None) -> object:
        seen.append(runtime.models.state)
        return open_worker(name, entry, preset)

    runtime.models._release = wrapped_release
    runtime.models._open = wrapped_open
    switched = client.post("/models/switch", json={"name": "aquaclear", "preset": "light"})
    assert switched.status_code == 200
    assert seen == ["unloading", "loading"]
    assert switched.json()["state"] == "ready"


def test_mark_finding_stores_raw_jpeg(client: TestClient) -> None:
    frames = client.post("/video/synthetic", json={"count": 1, "width": 32, "height": 24})
    frame_id = frames.json()["frame_ids"][0]
    marked = client.post("/findings", json={"frame_id": frame_id})
    assert marked.status_code == 200
    body = marked.json()
    path = Path(body["path"])
    assert path.suffix == ".jpg"
    assert path.is_file()
    video = client.app.state.settings.thresholds.video
    jpeg = encode_jpeg(
        gradient_bgr(32, 24, 0), 32, 24, video.display_max_side, video.display_jpeg_quality
    )
    assert body["sha256"] == hashlib.sha256(jpeg).hexdigest()
    listed = client.get("/findings").json()
    assert listed[0]["frame_id"] == frame_id
    with client.app.state.office.db.connect() as conn:
        row = conn.execute(
            "SELECT action FROM audit WHERE action='mark_finding' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert row is not None


def test_stream_skips_one_bad_frame(client: TestClient) -> None:
    frames = client.post("/video/synthetic", json={"count": 1, "width": 32, "height": 24})
    frame_id = frames.json()["frame_ids"][0]
    runtime = client.app.state.runtime
    original = runtime.display_packet
    state = {"failed": False}

    def flaky() -> tuple[dict[str, object], bytes | None]:
        if not state["failed"]:
            state["failed"] = True
            raise RuntimeError("frame tampilan")
        return original()

    runtime.display_packet = flaky  # type: ignore[method-assign]
    with client.websocket_connect("/video/stream") as socket:
        meta = socket.receive_json()
    assert meta["frame_id"] == frame_id
    assert meta["state"] == "live"


def test_stream_sends_frame_id_then_jpeg(client: TestClient) -> None:
    frames = client.post("/video/synthetic", json={"count": 1, "width": 32, "height": 24})
    frame_id = frames.json()["frame_ids"][0]
    with client.websocket_connect("/video/stream") as socket:
        meta = socket.receive_json()
        blob = socket.receive_bytes()
    assert meta["frame_id"] == frame_id
    assert meta["state"] == "live"
    assert blob[:2] == b"\xff\xd8"


def test_compare_stream_sends_the_display_jpeg(client: TestClient) -> None:
    frames = client.post("/video/synthetic", json={"count": 1, "width": 32, "height": 24})
    frame_id = frames.json()["frame_ids"][0]
    with client.websocket_connect("/video/compare-stream") as socket:
        meta = socket.receive_json()
        blob = socket.receive_bytes()
    assert meta["frame_id"] == frame_id
    assert meta["parts"] == 1
    assert blob[:2] == b"\xff\xd8"


def test_turbidity_stays_empty_until_thresholds_exist() -> None:
    cfg = TurbidityCfg()
    frame = StoredFrame("a", 0.0, 8, 8, bytes(8 * 8 * 3))
    assert configured(cfg) is False
    assert turbidity_level(frame, cfg) is None
    ranked = TurbidityCfg(rms_low_max=1, rms_medium_max=30)
    assert turbidity_level(frame, ranked) == "low"
