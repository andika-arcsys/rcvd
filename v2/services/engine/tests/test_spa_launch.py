from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from deepinsight_engine.api.app import create_app
from deepinsight_engine.api.spa import _static_file
from deepinsight_engine.gpu.tensorflow_mem import enable_memory_growth
from deepinsight_engine.launch import ensure_ui, gpu_mode_label, lan_pin_problem, python_ok


def test_python_must_be_3_12() -> None:
    assert python_ok((3, 12)) is None
    assert python_ok((3, 11)) is not None


def test_lan_requires_pin() -> None:
    assert lan_pin_problem([]) is not None
    assert lan_pin_problem(["  "]) is not None
    assert lan_pin_problem(["hash"]) is None


def test_gpu_mode_label() -> None:
    assert "GPU-001" in gpu_mode_label(False)
    assert "satu pekerja" in gpu_mode_label(True)


def test_memory_growth_when_tensorflow_missing() -> None:
    sys.modules.pop("tensorflow", None)
    if importlib.util.find_spec("tensorflow") is not None:
        return
    assert enable_memory_growth() == "tensorflow tidak terpasang"


def test_memory_growth_enables_devices() -> None:
    calls: list[object] = []
    tf = types.ModuleType("tensorflow")
    config = types.ModuleType("tensorflow.config")
    experimental = types.SimpleNamespace(set_memory_growth=lambda device, flag: calls.append(flag))
    config.list_physical_devices = lambda _kind: ["gpu0"]  # type: ignore[attr-defined]
    config.experimental = experimental  # type: ignore[attr-defined]
    tf.config = config  # type: ignore[attr-defined]
    sys.modules["tensorflow"] = tf
    try:
        assert "memory growth aktif" in enable_memory_growth()
        assert calls == [True]
    finally:
        del sys.modules["tensorflow"]


def test_ensure_ui_uses_existing_build(tmp_path: Path) -> None:
    index = tmp_path / "apps" / "desktop" / "dist" / "index.html"
    index.parent.mkdir(parents=True)
    index.write_text("ok", encoding="utf-8")
    assert ensure_ui(tmp_path) == index.parent


def test_ensure_ui_explains_missing_pnpm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("deepinsight_engine.launch.shutil.which", lambda _name: None)
    with pytest.raises(SystemExit, match="pnpm tidak ditemukan"):
        ensure_ui(tmp_path)


def test_ensure_ui_calls_resolved_pnpm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], cwd: Path, check: bool) -> None:
        calls.append(cmd)
        if cmd[-1] == "build":
            index = cwd / "apps" / "desktop" / "dist" / "index.html"
            index.parent.mkdir(parents=True, exist_ok=True)
            index.write_text("ui", encoding="utf-8")

    monkeypatch.setattr("deepinsight_engine.launch.shutil.which", lambda name: r"C:\pnpm.cmd")
    monkeypatch.setattr("deepinsight_engine.launch.subprocess.run", fake_run)
    ensure_ui(tmp_path)
    assert calls[0] == [r"C:\pnpm.cmd", "install"]
    assert calls[1][:3] == [r"C:\pnpm.cmd", "--filter", "@deepinsight/desktop"]


def test_spa_document_and_api(tmp_path: Path, config_dir: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>DeepInsight</title>", encoding="utf-8")
    assets = dist / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("console.log(1)", encoding="utf-8")
    app = create_app(config_dir=config_dir, data_dir=tmp_path / "data", ui_dir=dist)
    client = TestClient(app)
    page = client.get("/", headers={"Accept": "text/html"})
    assert "DeepInsight" in page.text
    script = client.get("/assets/app.js")
    assert script.status_code == 200
    assert "console" in script.text
    html_login = client.get("/login", headers={"Accept": "text/html"})
    assert html_login.status_code == 200
    assert "DeepInsight" in html_login.text
    missing = client.get("/tidak-ada")
    assert missing.status_code == 404
    assert missing.json()["code"] == "API-003"
    assert client.get("/health").json()["status"] == "ok"
    assert _static_file(dist.resolve(), "/assets/../../secrets.txt") is None
