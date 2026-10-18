"""Lokasi environment Python. Satu sumber: DEEPINSIGHT_VENV, lalu env.cfg, lalu deepenv."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping
from pathlib import Path

DEFAULT_NAME = "deepenv"
ENV_KEY = "DEEPINSIGHT_VENV"
CFG_NAME = "env.cfg"


def configured_dir(root: Path, environ: Mapping[str, str] | None = None) -> Path:
    """Folder environment. Relatif dihitung dari root v2."""
    raw = _raw(root, os.environ if environ is None else environ)
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    return path


def find_python(directory: Path) -> Path | None:
    """venv Windows, conda Windows (python.exe di akar), atau bin/python."""
    for candidate in _candidates(directory):
        if candidate.is_file():
            return candidate
    return None


def version_of(executable: Path) -> tuple[int, int] | None:
    try:
        out = subprocess.check_output(
            [str(executable), "-c", "import sys; print(sys.version_info[0], sys.version_info[1])"],
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    parts = out.split()
    if len(parts) != 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def assess(root: Path, environ: Mapping[str, str] | None = None) -> tuple[str, Path, Path | None]:
    """reuse, create, atau refuse. Tidak menghapus atau menimpa folder."""
    directory = configured_dir(root, environ)
    executable = find_python(directory)
    if executable is None:
        action = "create" if not directory.exists() else "refuse"
        return action, directory, None
    if version_of(executable) == (3, 12):
        return "reuse", directory, executable
    return "refuse", directory, executable


def missing_text(directory: Path) -> str:
    lines = [
        "Python environment tidak ditemukan.",
        "Dicari:",
        f"  {directory / 'Scripts' / 'python.exe'}",
        f"  {directory / 'python.exe'}",
        f"  {directory / 'bin' / 'python'}",
        "Jalankan setup.bat atau periksa env.cfg. Python sistem tidak dipakai.",
    ]
    return "\n".join(lines)


def same_env(prefix: Path, root: Path, environ: Mapping[str, str] | None = None) -> bool:
    return prefix.resolve() == configured_dir(root, environ).resolve()


def _raw(root: Path, environ: Mapping[str, str]) -> str:
    override = environ.get(ENV_KEY, "").strip().strip('"').strip("'")
    if override:
        return override
    from_file = _from_cfg(root / CFG_NAME)
    return from_file or DEFAULT_NAME


def _from_cfg(path: Path) -> str:
    if not path.is_file():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        if key.strip() == "VENV_DIR":
            return value.strip().strip('"').strip("'")
    return ""


def _candidates(directory: Path) -> tuple[Path, ...]:
    return (
        directory / "Scripts" / "python.exe",
        directory / "Scripts" / "python",
        directory / "python.exe",
        directory / "bin" / "python",
    )
