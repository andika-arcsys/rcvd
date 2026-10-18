"""Jalankan DeepInsight: satu proses Python, antarmuka di browser."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "services" / "engine"))

from deepinsight_engine.launch import prepare, serve  # noqa: E402


def main() -> None:
    args = _args()
    settings, _label = prepare(ROOT, lan=args.lan)
    host = "0.0.0.0" if args.lan else settings.app.engine.host
    port = args.port if args.port is not None else settings.app.engine.port
    serve(host, port, ROOT / "config", open_browser=not args.no_browser)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DeepInsight di browser")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--lan", action="store_true", help="dengar di 0.0.0.0; PIN wajib")
    parser.add_argument("--no-browser", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    main()
