"""Kalibrasi intrinsik dari foto papan catur.

Dari folder v2. `--squares` adalah jumlah sudut dalam, bukan jumlah kotak:

    .venv\\Scripts\\python scripts\\calibrate_camera.py --images D:\\kalibrasi\\foto ^
        --squares 9x6 --square-mm 25 --camera-id rov01
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "engine"))

from deepinsight_engine.camera_calib import calibrate_folder  # noqa: E402
from deepinsight_engine.core.paths import default_config_dir  # noqa: E402


def main() -> int:
    args = _parser().parse_args()
    corners = _corners(args.squares, args.corners_cols, args.corners_rows)
    if isinstance(corners, str):
        print(corners)
        return 2
    cols, rows = corners
    config_dir = args.config_dir or default_config_dir()
    code, message = calibrate_folder(
        config_dir,
        args.images,
        args.camera_id,
        args.square_mm,
        cols,
        rows,
    )
    print(message)
    return code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Kalibrasi kamera dari foto papan catur")
    parser.add_argument("--images", "--folder", dest="images", type=Path, required=True)
    parser.add_argument("--camera-id", "--id", dest="camera_id", required=True)
    parser.add_argument("--square-mm", type=float, required=True)
    parser.add_argument("--squares", default=None, help="sudut dalam, mis. 9x6")
    parser.add_argument("--corners-cols", type=int, default=None)
    parser.add_argument("--corners-rows", type=int, default=None)
    parser.add_argument("--config-dir", type=Path, default=None)
    return parser


def _corners(squares: str | None, cols: int | None, rows: int | None) -> tuple[int, int] | str:
    parsed = _parse_squares(squares) if squares else None
    if isinstance(parsed, str):
        return parsed
    if parsed is not None and cols is None and rows is None:
        return parsed
    if parsed is None and cols is not None and rows is not None:
        return cols, rows
    if parsed is not None and (cols, rows) == parsed:
        return parsed
    return "Isi --squares 9x6 (sudut dalam) atau --corners-cols bersama --corners-rows."


def _parse_squares(squares: str) -> tuple[int, int] | str:
    parts = squares.lower().replace("*", "x").split("x")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        return "--squares harus kolomxbaris sudut dalam, misalnya 9x6."
    return int(parts[0]), int(parts[1])


if __name__ == "__main__":
    sys.exit(main())
