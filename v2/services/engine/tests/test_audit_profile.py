from __future__ import annotations

import threading
from pathlib import Path

from deepinsight_engine.audit_profile import profile_session


def test_short_profile_reports_rss_and_stops_watchdog(tmp_path: Path) -> None:
    config = Path(__file__).resolve().parents[3] / "config"
    report = profile_session(config, tmp_path, 2)
    assert report["freezes"] == 2
    assert report["watchdog_alive"] is False
    assert report["workers"] == 0
    assert isinstance(report["rss_peak"], int)
    assert "di-watchdog" not in [item.name for item in threading.enumerate()]
