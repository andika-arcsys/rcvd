"""Tulis openapi.json dari aplikasi (sumber tipe TypeScript di packages/shared)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from deepinsight_engine.api.app import create_app


def main(target: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(data_dir=Path(tmp))
        spec = app.openapi()
    Path(target).write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
