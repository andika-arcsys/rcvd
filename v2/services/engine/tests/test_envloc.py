"""env.cfg, DEEPINSIGHT_VENV, conda, dan penolakan versi Python lain."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from deepinsight_engine.envloc import assess, configured_dir, missing_text

ROOT = Path(__file__).resolve().parents[3]


def _python(directory: Path, name: str, major_minor: str) -> Path:
    folder = directory / name
    folder.parent.mkdir(parents=True, exist_ok=True)
    folder.write_text(f"#!/bin/sh\necho {major_minor}\n", encoding="utf-8")
    folder.chmod(0o755)
    return folder


def test_relative_deepenv_and_default(tmp_path: Path) -> None:
    assert configured_dir(tmp_path, {}) == tmp_path / "deepenv"
    (tmp_path / "env.cfg").write_text("# catatan\nVENV_DIR=deepenv\n", encoding="utf-8")
    _python(tmp_path / "deepenv", "bin/python", "3 12")
    action, directory, executable = assess(tmp_path, {})
    assert action == "reuse"
    assert directory == tmp_path / "deepenv"
    assert executable == tmp_path / "deepenv" / "bin" / "python"


def test_absolute_path_in_env_cfg(tmp_path: Path) -> None:
    outside = tmp_path / "luar" / "conda"
    _python(outside, "python.exe", "3 12")
    (tmp_path / "env.cfg").write_text(f"VENV_DIR={outside}\n", encoding="utf-8")
    action, directory, executable = assess(tmp_path, {})
    assert action == "reuse"
    assert directory == outside
    assert executable == outside / "python.exe"


def test_environment_variable_overrides_env_cfg(tmp_path: Path) -> None:
    (tmp_path / "env.cfg").write_text("VENV_DIR=deepenv\n", encoding="utf-8")
    _python(tmp_path / "deepenv", "bin/python", "3 12")
    other = tmp_path / "override"
    _python(other, "bin/python", "3 12")
    action, directory, _executable = assess(tmp_path, {"DEEPINSIGHT_VENV": str(other)})
    assert action == "reuse"
    assert directory == other


def test_missing_python_message_lists_conda_and_venv() -> None:
    text = missing_text(Path("D:/Deepinsight/v2/deepenv"))
    assert "Scripts" in text and "python.exe" in text
    assert "setup.bat" in text and "env.cfg" in text
    assert "sistem" in text


def test_refuse_other_python_does_not_touch_the_file(tmp_path: Path) -> None:
    executable = _python(tmp_path / "deepenv", "python.exe", "3 11")
    before = executable.read_text(encoding="utf-8")
    action, _directory, found = assess(tmp_path, {})
    assert action == "refuse"
    assert found == executable
    assert executable.read_text(encoding="utf-8") == before


def test_create_when_folder_is_absent(tmp_path: Path) -> None:
    action, directory, executable = assess(tmp_path, {})
    assert action == "create"
    assert directory == tmp_path / "deepenv"
    assert executable is None
    assert not directory.exists()


def test_start_sh_fails_without_using_system_python(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["DEEPINSIGHT_VENV"] = str(tmp_path / "tidak-ada")
    result = subprocess.run(
        ["sh", "start.sh"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "Python:" not in result.stdout
    assert "python.exe" in result.stdout
    assert "env.cfg" in result.stdout
    assert "sistem" in result.stdout


def test_setup_sh_does_not_overwrite_other_version(tmp_path: Path) -> None:
    executable = _python(tmp_path / "condaenv", "python.exe", "3.11")
    before = executable.read_text(encoding="utf-8")
    env = os.environ.copy()
    env["DEEPINSIGHT_VENV"] = str(tmp_path / "condaenv")
    result = subprocess.run(
        ["sh", "setup.sh"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Tidak ditimpa" in result.stdout
    assert executable.read_text(encoding="utf-8") == before


def test_shell_resolver_relative_absolute_and_override(tmp_path: Path) -> None:
    (tmp_path / "env.cfg").write_text("VENV_DIR=deepenv\n", encoding="utf-8")
    script = (ROOT / "scripts" / "env.sh").read_text(encoding="utf-8")
    relative = subprocess.run(
        ["sh", "-c", f'{script}\nROOT="{tmp_path}"\nload_venv_dir\nprintf %s "$VENV_ABS"'],
        capture_output=True,
        text=True,
        check=True,
        env={"PATH": os.environ["PATH"]},
    )
    assert relative.stdout == f"{tmp_path}/deepenv"
    absolute = tmp_path / "abs" / "deepenv"
    (tmp_path / "env.cfg").write_text(f"VENV_DIR={absolute}\n", encoding="utf-8")
    got = subprocess.run(
        ["sh", "-c", f'{script}\nROOT="{tmp_path}"\nload_venv_dir\nprintf %s "$VENV_ABS"'],
        capture_output=True,
        text=True,
        check=True,
        env={"PATH": os.environ["PATH"]},
    )
    assert got.stdout == str(absolute)
    overridden = subprocess.run(
        ["sh", "-c", f'{script}\nROOT="{tmp_path}"\nload_venv_dir\nprintf %s "$VENV_ABS"'],
        capture_output=True,
        text=True,
        check=True,
        env={"PATH": os.environ["PATH"], "DEEPINSIGHT_VENV": str(tmp_path / "dari-env")},
    )
    assert overridden.stdout == str(tmp_path / "dari-env")


def test_start_py_prints_runtime_and_warns_on_mismatch(tmp_path: Path) -> None:
    code = "import start; start._report_python()"
    warned = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env={**os.environ, "DEEPINSIGHT_VENV": str(tmp_path / "lain")},
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Python:" in warned.stdout
    assert "Environment:" in warned.stdout
    assert "Peringatan" in warned.stdout
    matched = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env={**os.environ, "DEEPINSIGHT_VENV": sys_prefix()},
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Peringatan" not in matched.stdout


def sys_prefix() -> str:
    out = subprocess.check_output(
        [sys.executable, "-c", "import sys; print(sys.prefix)"],
        text=True,
    )
    return out.strip()


def test_start_bat_names_the_searched_paths() -> None:
    text = (ROOT / "start.bat").read_text(encoding="utf-8")
    assert r"Scripts\python.exe" in text
    assert r"python.exe" in text
    assert "setup.bat" in text
    assert "env.cfg" in text
    assert "sistem" in text
