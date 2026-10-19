from __future__ import annotations

from pathlib import Path

from deepinsight_engine.core.config import load_settings
from deepinsight_engine.video.frames import RingBuffer, StoredFrame
from deepinsight_engine.video.pipeline import FramePipeline

REPO_CONFIG = Path(__file__).resolve().parents[3] / "config"


def _frame(frame_id: str, at: float) -> StoredFrame:
    return StoredFrame(frame_id, at, 2, 2, b"\x00" * 12)


def test_ring_drops_frames_older_than_duration() -> None:
    ring = RingBuffer(3)
    ring.push(_frame("a", 0))
    ring.push(_frame("b", 1))
    ring.push(_frame("c", 4))
    assert ring.get("a") is None
    assert ring.get("b") is not None and ring.get("c") is not None
    assert len(ring) == 2


def test_lost_signal_after_configured_gap() -> None:
    video = load_settings(REPO_CONFIG).thresholds.video
    pipeline = FramePipeline(RingBuffer(video.ring_buffer_s), video, lambda _frame: None)
    pipeline.push(_frame("a", 10))
    assert pipeline.observe(10 + video.lost_signal_s) is None
    assert pipeline.observe(10 + video.lost_signal_s + 0.01) == "VID-001"
    assert pipeline.state == "lost"
    pipeline.push(_frame("b", 20))
    assert pipeline.state == "live"


def test_enhanced_frame_keeps_both_jpegs() -> None:
    video = load_settings(REPO_CONFIG).thresholds.video
    pipeline = FramePipeline(RingBuffer(video.ring_buffer_s), video, lambda frame: frame.bgr)
    pipeline.push(_frame("a", 1))
    shown = pipeline.last_display
    assert shown is not None and shown.enhanced
    assert shown.jpeg[:2] == b"\xff\xd8"
    assert shown.raw_jpeg is not None and shown.raw_jpeg[:2] == b"\xff\xd8"
