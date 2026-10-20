from __future__ import annotations

import threading
import time
from pathlib import Path

from deepinsight_engine.api.app import create_app
from deepinsight_engine.runtime import Runtime
from deepinsight_engine.video.frames import StoredFrame
from deepinsight_engine.video.live_infer import LiveInfer, publish_allowed

REPO_CONFIG = Path(__file__).resolve().parents[3] / "config"


def _frame(frame_id: str) -> StoredFrame:
    return StoredFrame(frame_id, 0.0, 2, 2, b"\x00" * 12)


def test_only_the_newest_frame_follows_the_one_in_flight() -> None:
    started = threading.Event()
    release = threading.Event()
    seen: list[str] = []

    def run(frame: StoredFrame, _generation: int) -> None:
        seen.append(frame.frame_id)
        if not started.is_set():
            started.set()
            release.wait(1)

    infer = LiveInfer(run)
    infer.submit(_frame("a"))
    assert started.wait(1)
    infer.submit(_frame("b"))
    infer.submit(_frame("c"))
    release.set()
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and seen != ["a", "c"]:
        time.sleep(0.01)
    assert seen == ["a", "c"]


def test_cancel_drops_the_result_of_the_model_being_replaced() -> None:
    started = threading.Event()
    release = threading.Event()
    published: list[int] = []

    def run(_frame_in: StoredFrame, generation: int) -> None:
        started.set()
        release.wait(1)
        if infer.accepts(generation):
            published.append(generation)

    infer = LiveInfer(run)
    infer.submit(_frame("a"))
    assert started.wait(1)
    infer.cancel()
    release.set()
    time.sleep(0.05)
    assert published == []


def test_submit_after_cancel_still_runs_the_new_frame() -> None:
    started = threading.Event()
    release = threading.Event()
    seen: list[str] = []

    def run(frame: StoredFrame, _generation: int) -> None:
        seen.append(frame.frame_id)
        if frame.frame_id == "a":
            started.set()
            release.wait(1)

    infer = LiveInfer(run)
    infer.submit(_frame("a"))
    assert started.wait(1)
    infer.cancel()
    infer.submit(_frame("b"))
    release.set()
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and seen != ["a", "b"]:
        time.sleep(0.01)
    assert seen == ["a", "b"]
    assert infer.accepts(1)


def test_a_failed_frame_does_not_stick_the_next_one() -> None:
    seen: list[str] = []

    def run(frame: StoredFrame, _generation: int) -> None:
        seen.append(frame.frame_id)
        if frame.frame_id == "a":
            raise RuntimeError("gagal")

    infer = LiveInfer(run)
    infer.submit(_frame("a"))
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and "a" not in seen:
        time.sleep(0.01)
    infer.submit(_frame("b"))
    while time.monotonic() < deadline and seen != ["a", "b"]:
        time.sleep(0.01)
    assert seen == ["a", "b"]


def test_camera_returns_before_hydro_finishes_and_a_replaced_model_is_dropped(
    tmp_path: Path,
) -> None:
    app = create_app(config_dir=REPO_CONFIG, data_dir=tmp_path)
    runtime = app.state.runtime
    assert isinstance(runtime, Runtime)
    runtime.models.state = "ready"
    runtime.models.active = "hydrodetect"
    started = threading.Event()
    release = threading.Event()

    def infer(frame: StoredFrame) -> None:
        started.set()
        release.wait(2)
        runtime.models.last_result = {
            "kind": "hydrodetect",
            "frame_id": frame.frame_id,
            "candidates": [],
        }

    runtime.models.infer = infer  # type: ignore[method-assign]
    begun = time.monotonic()
    runtime.push_synthetic(1, 8, 8)
    assert time.monotonic() - begun < 0.5
    assert runtime.pipeline.last_display is not None
    assert runtime.pipeline.last_display.enhanced is False
    assert started.wait(1)
    release.set()
    assert _wait_kind(runtime, "hydrodetect")
    started.clear()
    release.clear()
    runtime.push_synthetic(1, 8, 8)
    assert started.wait(1)
    runtime.switch("optical", None)
    release.set()
    deadline = time.monotonic() + 0.3
    while time.monotonic() < deadline:
        assert runtime.vision_view()["kind"] is None
        time.sleep(0.01)


def _wait_kind(runtime: Runtime, kind: str) -> bool:
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        if runtime.vision_view()["kind"] == kind:
            return True
        time.sleep(0.01)
    return False


def test_publish_requires_the_same_ready_model() -> None:
    assert publish_allowed("hydrodetect", "hydrodetect", "ready")
    assert not publish_allowed("spatialsight", "hydrodetect", "ready")
    assert not publish_allowed("hydrodetect", "hydrodetect", "unloading")
    assert not publish_allowed(None, "hydrodetect", "ready")
