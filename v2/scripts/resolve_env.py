"""Cetak folder environment atau pesan bila Python-nya tidak ada. Hanya pustaka standar."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "engine"))

from deepinsight_engine.envloc import configured_dir, find_python, missing_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Lokasi Python DeepInsight")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--print-python", action="store_true")
    parser.add_argument("--missing", action="store_true")
    args = parser.parse_args()
    directory = configured_dir(args.root.resolve())
    if args.missing or not args.print_python:
        executable = find_python(directory)
        if executable is None:
            print(missing_text(directory))
            return 1
        print(executable if args.print_python or args.missing else directory)
        return 0
    executable = find_python(directory)
    if executable is None:
        print(missing_text(directory))
        return 1
    print(executable)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
