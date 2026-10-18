"""Profil 200 FREEZE dan ganti fitur. VRAM hanya terisi bila GPU NVIDIA ada.

Jalankan dari folder v2:

    .venv/bin/python scripts/profile_session.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "engine"))

from deepinsight_engine.audit_profile import profile_session
from deepinsight_engine.core.paths import default_config_dir


def main() -> int:
    with tempfile.TemporaryDirectory() as folder:
        report = profile_session(default_config_dir(), Path(folder), 200)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
