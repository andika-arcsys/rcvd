"""Lokasi folder: config, data, dan sesi."""

from __future__ import annotations

import os
import sys
from pathlib import Path

CONFIG_ENV = "DEEPINSIGHT_CONFIG_DIR"
DATA_ENV = "DEEPINSIGHT_DATA_DIR"


def default_config_dir() -> Path:
    env = os.environ.get(CONFIG_ENV)
    if env:
        return Path(env)
    return _repo_config()


def _repo_config() -> Path:
    # .../v2/services/engine/deepinsight_engine/core/paths.py -> .../v2/config
    return Path(__file__).resolve().parents[4] / "config"


def default_data_dir(configured: str | None) -> Path:
    env = os.environ.get(DATA_ENV)
    if env:
        return Path(env)
    if configured:
        return Path(configured)
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "DeepInsight"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "DeepInsight"
