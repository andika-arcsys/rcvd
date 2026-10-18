from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from deepinsight_engine.api.app import create_app

REPO_CONFIG = Path(__file__).resolve().parents[3] / "config"


@pytest.fixture
def config_dir() -> Path:
    return REPO_CONFIG


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(config_dir=REPO_CONFIG, data_dir=tmp_path)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def secured_client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(config_dir=REPO_CONFIG, data_dir=tmp_path, token="rahasia-uji")
    with TestClient(app) as test_client:
        yield test_client
