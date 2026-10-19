"""Depth Anything 3 pada CUDA, sama dengan adapter konsol.

``DepthAnything3.from_pretrained`` lalu ``to(cuda).eval()``. Inferensi memakai
``process_res`` dan ``export_format="mini_npz"``. Kedalaman DA3 bersifat
focal-normalized: pratinjau live tetap relatif, dan angka jarak hanya dihitung
pada frame beku lewat skala referensi.
"""

from __future__ import annotations

import importlib
from typing import Any

from ..core.errors import EngineError
from .budget import cuda_status_note, try_limit_process_memory

PROCESS_SIZES = (378, 504, 672)
DEFAULT_RES = 504
DEFAULT_MODEL = "depth-anything/DA3METRIC-LARGE"
DA3_WARNINGS = (
    "DA3 K/depth belum dikalibrasi untuk koordinat kamera underwater.",
    "Reference scale hanya valid pada frozen frame yang sama.",
)


def clamp_res(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return DEFAULT_RES
    if value in PROCESS_SIZES:
        return value
    return DEFAULT_RES


def load_model(
    model_id: str,
    vram_budget_mb: float,
    gpu_max_pct: float,
    process_res: int,
) -> tuple[dict[str, Any], str, bool]:
    """Muat DA3METRIC. Kegagalan pemanasan tetap mengembalikan model yang sudah di GPU."""
    torch = _torch()
    if not bool(torch.cuda.is_available()):
        raise EngineError("MDL-003", "CUDA Depth Anything 3")
    cap = try_limit_process_memory(torch, vram_budget_mb)
    model = _open(torch, model_id)
    bundle: dict[str, Any] = {"model": model, "torch": torch, "half": True, "model_id": model_id}
    half = _warm(bundle, process_res)
    bundle["half"] = half
    suffix = "half" if half else "fp32"
    note = cuda_status_note(torch, cap, gpu_max_pct, 0, suffix)
    return bundle, note, half


def infer_depth(bundle: dict[str, Any], frame_bgr: Any, process_res: int) -> Any:
    """Satu citra BGR. Hasilnya kisi kedalaman pada ukuran frame, bukan meter."""
    cv2 = importlib.import_module("cv2")
    np = importlib.import_module("numpy")
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    prediction = _invoke(bundle, rgb, process_res)
    depth = np.asarray(prediction.depth[0], dtype=np.float32)
    if depth.shape[:2] != rgb.shape[:2]:
        depth = cv2.resize(depth, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_LINEAR)
    return depth.astype(np.float32)


def _torch() -> Any:
    try:
        return importlib.import_module("torch")
    except ImportError as exc:
        raise EngineError("MDL-002", "torch belum terpasang") from exc


def _open(torch: Any, model_id: str) -> Any:
    try:
        api = importlib.import_module("depth_anything_3.api")
    except ImportError as exc:
        raise EngineError(
            "MDL-002",
            "paket depth_anything_3 belum terpasang. "
            "Clone ByteDance-Seed/Depth-Anything-3 lalu pip install -e .",
        ) from exc
    try:
        model = api.DepthAnything3.from_pretrained(model_id)
        return model.to(torch.device("cuda:0")).eval()
    except Exception as exc:  # noqa: BLE001 - unduh dan muat Hugging Face melempar error beragam
        raise EngineError("MDL-002", f"Depth Anything 3 gagal dimuat: {exc}") from exc


def _warm(bundle: dict[str, Any], process_res: int) -> bool:
    np = importlib.import_module("numpy")
    blank = np.zeros((32, 32, 3), dtype=np.uint8)
    try:
        infer_depth(bundle, blank, process_res)
    except Exception:  # noqa: BLE001 - fp16 gagal, coba fp32 lalu tetap buka layar
        bundle["half"] = False
        try:
            infer_depth(bundle, blank, process_res)
        except Exception:  # noqa: BLE001 - fp32 juga gagal, layar tetap terbuka
            return False
        return False
    return True


def _invoke(bundle: dict[str, Any], rgb: Any, process_res: int) -> Any:
    torch = bundle["torch"]
    model = bundle["model"]
    size = clamp_res(process_res)
    with torch.inference_mode():
        if bundle.get("half"):
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                return model.inference(image=[rgb], process_res=size, export_format="mini_npz")
        return model.inference(image=[rgb], process_res=size, export_format="mini_npz")
