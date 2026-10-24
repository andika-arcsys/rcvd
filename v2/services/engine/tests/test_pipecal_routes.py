from __future__ import annotations

import io
import shutil
import sys
from pathlib import Path

import numpy as np
import yaml
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))
from pipecal_scene import RADIUS, make_scene, noisy_clicks  # noqa: E402
from test_camera_calibration import PIN  # noqa: E402

from deepinsight_engine.api.app import create_app  # noqa: E402
from deepinsight_engine.pipecal.measure import ray_cylinder  # noqa: E402

REPO_CONFIG = Path(__file__).resolve().parents[3] / "config"


def _client(tmp_path: Path) -> TestClient:
    cfg = tmp_path / "cfg"
    shutil.copytree(REPO_CONFIG, cfg)
    body = {
        "schema_version": 1,
        "id": "rov01",
        "image_width": 1280,
        "image_height": 720,
        "camera_matrix": [1050.0, 0.0, 640.0, 0.0, 1050.0, 360.0, 0.0, 0.0, 1.0],
        "dist_coeffs": [-0.12, 0.03, 0.0005, -0.0004, 0.0],
    }
    (cfg / "cameras" / "rov01.yaml").write_text(yaml.safe_dump(body), encoding="utf-8")
    client = TestClient(create_app(config_dir=cfg, data_dir=tmp_path / "data"))
    client.__enter__()
    assert client.post("/auth/login", json={"user_id": "uji", "pin": PIN}).status_code == 200
    return client


def _payload(psi: float = 34.0) -> tuple[dict[str, object], object]:
    sc = make_scene(psi)
    top, bot = noisy_clicks(sc, 7, 0.5)
    return {
        "role": "ahli_ukur",
        "camera_id": "rov01",
        "width": 1280,
        "height": 720,
        "diameter_cm": RADIUS * 2,
        "d_type": "pi-tape",
        "top": top.tolist(),
        "bot": bot.tolist(),
    }, sc


def test_solve_and_measure_length(tmp_path: Path) -> None:
    client = _client(tmp_path)
    body, sc = _payload()
    locked = client.post("/pipecal/solve", json={**body, "role": "manajemen"})
    assert locked.status_code in (403, 422)
    out = client.post("/pipecal/solve", json=body)
    assert out.status_code == 200, out.text
    data = out.json()
    assert data["passed"] and data["status"] in ("VALID", "VALID-TERBATAS")
    p1 = sc.cam.project((sc.c0 + 20 * sc.d)[None])[0].tolist()
    p2 = sc.cam.project((sc.c0 + 180 * sc.d)[None])[0].tolist()
    m = client.post(
        "/pipecal/measure", json={**body, "kind": "length", "points": [p1, p2], "n_mc": 40}
    )
    assert m.status_code == 200, m.text
    res = m.json()
    assert abs(res["value"] / 160 - 1) < 0.03
    assert res["p025"] <= res["value"] <= res["p975"] or res["p025"] < 160 < res["p975"]


def test_measure_rejects_wrong_point_count(tmp_path: Path) -> None:
    client = _client(tmp_path)
    body, _ = _payload()
    bad = client.post("/pipecal/measure", json={**body, "kind": "length", "points": [[1, 1]]})
    assert bad.status_code in (400, 422)


def test_depth_fit_recovers_scale(tmp_path: Path) -> None:
    client = _client(tmp_path)
    body, sc = _payload()
    a_true, b_true = 2.0, 0.002
    v, u = np.mgrid[0:720, 0:1280]
    rays = sc.cam.rays(np.column_stack([u.ravel(), v.ravel()]).astype(float))
    z = np.full(len(rays), 400.0)
    for i, r in enumerate(rays):
        lam = ray_cylinder(r, sc.c0, sc.d, RADIUS)
        if lam is not None:
            z[i] = lam * r[2]
    m = ((1.0 / z - b_true) / a_true).reshape(720, 1280).astype(np.float32)
    buf = io.BytesIO()
    np.save(buf, m)
    form = {
        k: str(body[k]) if not isinstance(body[k], list) else __import__("json").dumps(body[k])
        for k in body
    }
    res = client.post(
        "/pipecal/depth",
        data={**form, "kind": "disparity"},
        files={"tensor": ("m.npy", buf.getvalue(), "application/octet-stream")},
    )
    assert res.status_code == 200, res.text
    out = res.json()
    assert abs(out["a"] - a_true) / a_true < 0.1
    assert out["n_pixels"] > 100
