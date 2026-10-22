"""Siapkan dan jalankan layanan web: cek Python, paket, GPU, lalu uvicorn."""

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from collections.abc import Sequence
from pathlib import Path

import uvicorn

from .api.app import create_app
from .core.config import Settings, load_settings
from .core.paths import default_config_dir
from .diagnostics import probe_gpu
from .stop import run_until_stopped

REQUIRED = ("fastapi", "uvicorn", "yaml", "cv2", "numpy", "pydantic", "argon2")
UI_FILTER = "@deepinsight/desktop"


def python_ok(version: tuple[int, int] | None = None) -> str | None:
    found = version if version is not None else sys.version_info[:2]
    if found != (3, 12):
        return f"Perlu Python 3.12. Yang dipakai: {found[0]}.{found[1]}."
    return None


def missing_packages(names: Sequence[str] = REQUIRED) -> list[str]:
    missing: list[str] = []
    for name in names:
        try:
            importlib.import_module(name)
        except ImportError:
            missing.append(name)
    return missing


def gpu_mode_label(available: bool) -> str:
    if available:
        return "Mode GPU: model dimuat saat fitur dibuka, satu pekerja."
    return "Mode terbatas: GPU tidak terbaca (GPU-001). AquaClear di CPU."


def lan_pin_problem(pin_hashes: Sequence[str]) -> str | None:
    if not pin_hashes or any(not item.strip() for item in pin_hashes):
        return "Mode LAN menolak jalan tanpa akun PIN di config/users.yaml."
    return None


def ensure_ui(root: Path, build: bool = True) -> Path:
    dist = root / "apps" / "desktop" / "dist"
    index = dist / "index.html"
    if index.is_file() or not build:
        if not index.is_file():
            raise SystemExit("UI belum dibangun. Jalankan build desktop.")
        return dist
    pnpm = shutil.which("pnpm")
    if pnpm is None:
        raise SystemExit(_pnpm_missing())
    if not (root / "node_modules").is_dir():
        _run_ui([pnpm, "install"], root)
    _run_ui([pnpm, "--filter", UI_FILTER, "build"], root)
    if not index.is_file():
        raise SystemExit("Build UI selesai tetapi index.html tidak ada.")
    return dist


def _run_ui(cmd: list[str], root: Path) -> None:
    try:
        subprocess.run(cmd, cwd=root, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"Build UI gagal ({cmd[0]}): {exc}") from exc


def _pnpm_missing() -> str:
    return (
        "UI belum ada: apps\\desktop\\dist\\index.html.\n"
        "Tampilan sudah ikut di dalam kode. Dari folder v2 jalankan git pull, lalu start.bat.\n"
        "Paket Python dipasang dengan setup.bat (pip). pnpm tidak dipakai di laptop."
    )


def pin_hashes(settings: Settings) -> list[str]:
    return [account.pin_hash for account in settings.users.users]


def serve(
    host: str,
    port: int,
    config_dir: Path,
    open_browser: bool,
) -> None:
    app = create_app(config_dir=config_dir)
    if open_browser:
        _open_later(host, port)
    run_until_stopped(lambda: uvicorn.run(app, host=host, port=port, log_config=None))


def prepare(root: Path, lan: bool, config_dir: Path | None = None) -> tuple[Settings, str]:
    problem = python_ok()
    if problem:
        raise SystemExit(problem)
    missing = missing_packages()
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(f"Paket belum lengkap: {joined}. Jalankan setup.sh atau setup.bat.")
    cfg_dir = config_dir or default_config_dir()
    settings = load_settings(cfg_dir)
    if lan:
        pin_problem = lan_pin_problem(pin_hashes(settings))
        if pin_problem:
            raise SystemExit(pin_problem)
    ensure_ui(root)
    from .gpu.depth_anything3_runtime import quiet_unused_gsplat

    quiet_unused_gsplat()
    info = probe_gpu()
    print(gpu_mode_label(info.available))
    return settings, gpu_mode_label(info.available)


def _open_later(host: str, port: int) -> None:
    shown = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    url = f"http://{shown}:{port}/"

    def _wait() -> None:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if _health_up(shown, port):
                print(f"Membuka browser {url}")
                webbrowser.open(url)
                return
            time.sleep(0.2)
        print(f"Layanan belum menjawab. Buka manual: {url}")

    threading.Thread(target=_wait, name="di-open-browser", daemon=True).start()


def _health_up(host: str, port: int) -> bool:
    import urllib.request

    try:
        with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=0.4) as response:
            return int(response.status) == 200
    except OSError:
        return False
