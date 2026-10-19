"""Apple Depth Pro pada interpreter engine, CUDA yang sama dengan Ultralytics."""

from __future__ import annotations

import importlib
from dataclasses import replace
from pathlib import Path
from typing import Any

from ..core.errors import EngineError
from .budget import cuda_status_note, try_limit_process_memory


def load_depth_pro(
    checkpoint: Path, vram_budget_mb: float = 0, gpu_max_pct: float = 90
) -> dict[str, Any]:
    torch = _torch()
    if not bool(torch.cuda.is_available()):
        raise EngineError("MDL-003", "CUDA Depth Pro")
    cap = try_limit_process_memory(torch, vram_budget_mb)
    package = _package()
    device = torch.device("cuda")
    config = _checkpoint_config(checkpoint)
    try:
        model, transform = package.create_model_and_transforms(
            device=device,
            precision=torch.float16,
            config=config,
        )
        model.eval()
    except EngineError:
        raise
    except Exception as exc:  # noqa: BLE001 - Depth Pro melempar error muat yang beragam
        raise EngineError("MDL-002", "checkpoint Depth Pro tidak dapat dibuka") from exc
    note = cuda_status_note(torch, cap, gpu_max_pct, device, "half")
    return {
        "model": model,
        "transform": transform,
        "device": device,
        "torch": torch,
        "note": note,
    }


def infer_meters(bundle: dict[str, Any], frame_bgr: Any) -> tuple[Any, float | None]:
    cv2 = importlib.import_module("cv2")
    np = importlib.import_module("numpy")
    torch = bundle["torch"]
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    image = bundle["transform"](rgb).to(bundle["device"])
    with torch.inference_mode():
        prediction = bundle["model"].infer(image)
    depth = prediction["depth"].detach().float().cpu().numpy()
    if depth.shape[:2] != rgb.shape[:2]:
        depth = cv2.resize(depth, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_LINEAR)
    return depth.astype(np.float32), _focal(prediction.get("focallength_px"))


def _torch() -> Any:
    try:
        return importlib.import_module("torch")
    except ImportError as exc:
        raise EngineError("MDL-002", "torch belum terpasang") from exc


def _package() -> Any:
    try:
        return importlib.import_module("depth_pro")
    except ImportError as exc:
        raise EngineError("MDL-002", "paket depth_pro belum terpasang di Python ini") from exc


def _checkpoint_config(checkpoint: Path) -> Any:
    module = importlib.import_module("depth_pro.depth_pro")
    return replace(module.DEFAULT_MONODEPTH_CONFIG_DICT, checkpoint_uri=str(checkpoint))


def _focal(value: Any) -> float | None:
    if value is None:
        return None
    if hasattr(value, "detach"):
        return float(value.detach().cpu().item())
    return float(value)
