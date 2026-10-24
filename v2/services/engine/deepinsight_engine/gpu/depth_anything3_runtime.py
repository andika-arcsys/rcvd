"""Depth Anything 3 pada CUDA, sama dengan adapter konsol.

``DepthAnything3.from_pretrained`` lalu ``to(cuda).eval()``. Inferensi memakai
``process_res`` dan ``export_format="mini_npz"``. Kedalaman DA3 bersifat
focal-normalized: pratinjau live tetap relatif, dan angka jarak hanya dihitung
pada frame beku lewat skala referensi.
"""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from typing import Any

from ..core.errors import EngineError
from ..spatial.da3_frame import (
    PROCESS_METHOD,
    ProcessGeometry,
    align_map,
    geometry_for_map,
)
from .budget import cuda_status_note, try_limit_process_memory

_INSTALL = (
    "paket depth_anything_3 belum terpasang. "
    "Clone ByteDance-Seed/Depth-Anything-3 lalu pip install -e ."
)
# Depth Anything 3 mengimpor addict, tetapi pyproject.toml tidak mencantumkannya.
_KNOWN_GAPS = {
    "addict": (
        "ketergantungan addict belum terpasang. "
        "Depth Anything 3 mengimpornya, tetapi pip install -e . tidak memasangnya. "
        "Di deepenv yang sama: python -m pip install addict"
    ),
}

PROCESS_SIZES = (378, 504, 672)
DEFAULT_RES = 504
DEFAULT_MODEL = "depth-anything/DA3METRIC-LARGE"
DA3_WARNINGS = (
    "DA3 K/depth belum dikalibrasi untuk koordinat kamera underwater.",
    "Reference scale hanya valid pada frozen frame yang sama.",
)


@dataclass
class Da3Observation:
    depth: Any
    conf: Any
    raw_intrinsics: Any
    geometry: ProcessGeometry
    process_res: int
    resize_method: str
    model_id: str
    checkpoint: str
    matched: bool


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
    bundle: dict[str, Any] = {
        "model": model,
        "torch": torch,
        "half": True,
        "model_id": model_id,
        "checkpoint": str(getattr(model, "_deepinsight_checkpoint", "") or ""),
    }
    half = _warm(bundle, process_res)
    bundle["half"] = half
    suffix = "half" if half else "fp32"
    note = cuda_status_note(torch, cap, gpu_max_pct, 0, suffix)
    return bundle, note, half


def infer_depth(bundle: dict[str, Any], frame_bgr: Any, process_res: int) -> Any:
    """Satu citra BGR. Hasilnya kisi kedalaman pada ukuran frame, bukan meter."""
    return infer_observation(bundle, frame_bgr, process_res).depth


def infer_observation(bundle: dict[str, Any], frame_bgr: Any, process_res: int) -> Da3Observation:
    """Kedalaman, conf, dan intrinsik pada koordinat PNG."""
    cv2 = importlib.import_module("cv2")
    np = importlib.import_module("numpy")
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    prediction = _invoke(bundle, rgb, process_res)
    height, width = int(rgb.shape[0]), int(rgb.shape[1])
    depth = np.asarray(prediction.depth[0], dtype=np.float32)
    conf = _optional_map(np, getattr(prediction, "conf", None))
    raw_k = _optional_matrix(np, getattr(prediction, "intrinsics", None))
    geom = geometry_for_map(width, height, clamp_res(process_res), PROCESS_METHOD, depth.shape[:2])
    aligned = align_map(depth, geom, nearest=False)
    same = conf is not None and conf.shape[:2] == depth.shape[:2]
    aligned_conf = None if not same else align_map(conf, geom, nearest=True)
    return Da3Observation(
        depth=aligned.astype(np.float32),
        conf=None if aligned_conf is None else aligned_conf.astype(np.float32),
        raw_intrinsics=raw_k,
        geometry=geom,
        process_res=clamp_res(process_res),
        resize_method=PROCESS_METHOD,
        model_id=str(bundle.get("model_id") or DEFAULT_MODEL),
        checkpoint=str(bundle.get("checkpoint") or ""),
        matched=geom.matched,
    )


def _optional_map(np: Any, value: Any) -> Any:
    if value is None:
        return None
    grid = np.asarray(value, dtype=np.float32)
    if grid.ndim == 3:
        grid = grid[0]
    if grid.ndim != 2:
        return None
    return grid


def _optional_matrix(np: Any, value: Any) -> Any:
    if value is None:
        return None
    matrix = np.asarray(value, dtype=np.float64)
    if matrix.ndim == 3:
        matrix = matrix[0]
    if matrix.shape != (3, 3):
        return None
    return matrix


def _torch() -> Any:
    try:
        return importlib.import_module("torch")
    except ImportError as exc:
        raise EngineError("MDL-002", "torch belum terpasang") from exc


def quiet_unused_gsplat() -> None:
    """Sembunyikan peringatan cabang 3DGS. Kedalaman metrik tidak memakai gsplat."""
    module = _logger_module()
    if module is None:
        return
    logger = getattr(module, "logger", None)
    if logger is None:
        return
    original = getattr(logger, "warn", None)
    if original is None or getattr(original, "_skips_gsplat", False):
        return

    def warn(*args: Any, **kwargs: Any) -> None:
        text = " ".join(str(item) for item in args)
        if "gsplat" in text or "3DGS" in text:
            return
        original(*args, **kwargs)

    wrapped: Any = warn
    wrapped._skips_gsplat = True
    logger.warn = wrapped


def _logger_module() -> Any | None:
    try:
        return importlib.import_module("depth_anything_3.utils.logger")
    except (ImportError, ValueError):
        return None


def _open(torch: Any, model_id: str) -> Any:
    _prepare_resolver()
    quiet_unused_gsplat()
    try:
        api = importlib.import_module("depth_anything_3.api")
    except ImportError as exc:
        _drop_partial_da3()
        raise EngineError("MDL-002", _import_detail(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - impor DA3 dapat melempar resolver OmegaConf
        _drop_partial_da3()
        raise EngineError("MDL-002", f"Depth Anything 3 gagal dimuat: {exc}") from exc
    try:
        model = api.DepthAnything3.from_pretrained(model_id)
        placed = model.to(torch.device("cuda:0")).eval()
        commit = getattr(placed, "_commit_hash", None)
        if commit:
            placed._deepinsight_checkpoint = str(commit)
        return placed
    except Exception as exc:  # noqa: BLE001 - unduh dan muat Hugging Face melempar error beragam
        raise EngineError("MDL-002", f"Depth Anything 3 gagal dimuat: {exc}") from exc


def _prepare_resolver() -> None:
    """cfg.py DA3 mendaftarkan resolver eval saat impor. Pendaftaran kedua menggagalkan muat."""
    try:
        module = importlib.import_module("omegaconf")
    except ImportError:
        return
    omega: Any = getattr(module, "OmegaConf", None)
    if omega is None or getattr(omega, "_deepinsight_eval_guard", False):
        return
    modern = getattr(omega, "register_resolver", None)
    legacy = getattr(omega, "register_new_resolver", None)
    target = modern if modern is not None else legacy
    if target is None:
        return
    guarded = _guard_register(target, getattr(omega, "has_resolver", None))
    if modern is not None:
        omega.register_resolver = guarded
    if legacy is not None:
        omega.register_new_resolver = guarded
    omega._deepinsight_eval_guard = True


def _guard_register(original: Any, has_resolver: Any) -> Any:
    def safe(name: str, resolver: Any, *args: Any, **kwargs: Any) -> None:
        if has_resolver is not None:
            try:
                if bool(has_resolver(name)):
                    return
            except Exception:  # noqa: BLE001,S110 - gagal cek resolver tetap boleh mencoba daftar
                pass
        try:
            original(name, resolver, *args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - pesan resolver sudah terdaftar ditelan, sisanya naik
            if _already_registered(exc):
                return
            raise

    return safe


def _already_registered(exc: Exception) -> bool:
    text = str(exc).lower()
    return "already registered" in text or "already exists" in text


def _import_detail(exc: ImportError) -> str:
    missing = exc.name or _name_from_message(str(exc))
    if missing in _KNOWN_GAPS:
        return _KNOWN_GAPS[missing]
    if missing in {"", "depth_anything_3"}:
        return _INSTALL
    if missing.startswith("depth_anything_3."):
        return (
            f"paket depth_anything_3 tidak lengkap ({missing}). "
            "Clone ByteDance-Seed/Depth-Anything-3 lalu pip install -e ."
        )
    return (
        f"ketergantungan Depth Anything 3 belum terpasang: {missing}. "
        "Di deepenv yang sama jalankan pip install -e . pada clone "
        "ByteDance-Seed/Depth-Anything-3."
    )


def _name_from_message(text: str) -> str:
    marker = "No module named "
    if marker not in text:
        return ""
    raw = text.split(marker, 1)[1].strip().strip(".")
    return raw.strip("'\"")


def _drop_partial_da3() -> None:
    prefix = "depth_anything_3"
    for key in list(sys.modules):
        if key == prefix or key.startswith(f"{prefix}."):
            del sys.modules[key]


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
                return model.inference(
                    image=[rgb],
                    process_res=size,
                    process_res_method=PROCESS_METHOD,
                    export_format="mini_npz",
                )
        return model.inference(
            image=[rgb],
            process_res=size,
            process_res_method=PROCESS_METHOD,
            export_format="mini_npz",
        )
