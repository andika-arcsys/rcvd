from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

OPENAPI_FILE = Path(__file__).resolve().parents[3] / "packages" / "shared" / "openapi.json"


def test_committed_openapi_matches_app(client: TestClient) -> None:
    committed = json.loads(OPENAPI_FILE.read_text(encoding="utf-8"))
    assert client.app.openapi() == committed, (  # type: ignore[attr-defined]
        "OpenAPI berubah. Jalankan `make gen` lalu commit packages/shared."
    )
