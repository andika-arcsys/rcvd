"""Kalibrasi intrinsik dari foto papan catur. Menolak bila ambang RMS kosong atau terlewati.

Dari folder v2:

    .venv/bin/python scripts/calibrate_camera.py --folder FOTO --id CAM \\
        --square-mm 25 --corners-cols 9 --corners-rows 6
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "engine"))

from deepinsight_engine.camera_calib import calibrate_folder
from deepinsight_engine.core.paths import default_config_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Kalibrasi kamera dari foto papan catur")
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--square-mm", type=float, required=True)
    parser.add_argument("--corners-cols", type=int, required=True)
    parser.add_argument("--corners-rows", type=int, required=True)
    parser.add_argument("--config-dir", type=Path, default=None)
    args = parser.parse_args()
    config_dir = args.config_dir or default_config_dir()
    code, message = calibrate_folder(
        config_dir,
        args.folder,
        args.id,
        args.square_mm,
        args.corners_cols,
        args.corners_rows,
    )
    print(message)
    return code


if __name__ == "__main__":
    sys.exit(main())
