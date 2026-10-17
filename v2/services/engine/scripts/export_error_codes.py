"""Tulis docs/ERROR_CODES.md dari registri kode error."""

from __future__ import annotations

import sys
from pathlib import Path

from deepinsight_engine.core.errors import render_error_codes_markdown


def main(target: str) -> None:
    Path(target).write_text(render_error_codes_markdown(), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
