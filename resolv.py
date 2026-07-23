"""RESOLV — Image Resolution Lab, integrated as a separate tool page.

Adapted from https://github.com/angslhn/RESOLV. Provides a self-contained
dark-mode image upscaler/downscaler mounted under ``/resolv`` inside the
PyCameraServer clone Flask app.

Scale logic (single slider, 0.25x - 4x):
  * 0.25x - 0.99x  -> downscale with OpenCV INTER_AREA (no AI)
  * 1.00x          -> noop, original returned unchanged
  * 1.01x - 4.00x  -> upscale with Real-ESRGAN ncnn-vulkan, then resized to
                      the exact target dimensions

Upscaling relies on the external ``realesrgan-ncnn-vulkan`` binary (named
``realesrgan.exe`` on Windows) plus its ``.param``/``.bin`` model files. These
large assets are not committed to the repository; drop them in place (see the
placeholder READMEs under ``bin/`` and ``models/realesrgan/``). If the binary or
a model is missing, upscale requests fail with a clear message while downscale
and noop keep working.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import time
import unicodedata
import uuid
from pathlib import Path

import cv2
from flask import Blueprint, jsonify, render_template, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "resolv_uploads"
OUTPUT_DIR = BASE_DIR / "static" / "resolv_outputs"
MODELS_DIR = BASE_DIR / "models" / "realesrgan"

# Candidate binary names, searched in the repo root and ./bin.
EXE_CANDIDATES = ["realesrgan.exe", "realesrgan-ncnn-vulkan", "realesrgan-ncnn-vulkan.exe"]
EXE_SEARCH_DIRS = [BASE_DIR, BASE_DIR / "bin"]

ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "bmp"}
MAX_DIMENSION = 2048
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
NATIVE_SCALE = 4  # every bundled model is x4
TILE_SIZE = 0  # 0 = auto; raise to 512/256 if VRAM < 4 GB
UPSCALE_TIMEOUT = 600  # seconds

MODEL_CHOICES = {
    "realesrgan-x4plus": {
        "label": "RealESRGAN - General",
        "desc": "Model serbaguna. Cocok untuk foto, render produk, aset game/UI.",
    },
    "realesrgan-x4plus-anime": {
        "label": "RealESRGAN - Anime",
        "desc": "Dioptimalkan untuk ilustrasi & line-art bergaya anime/kartun.",
    },
    "realesr-animevideov3-x4": {
        "label": "RealESRGAN - Anime Video",
        "desc": "Versi ringan, dibuat untuk frame video anime, lebih cepat.",
    },
}

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

resolv_bp = Blueprint("resolv", __name__)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def find_exe() -> str | None:
    for directory in EXE_SEARCH_DIRS:
        for name in EXE_CANDIDATES:
            candidate = directory / name
            if candidate.is_file():
                return str(candidate)
    return None


def model_files_present(model: str) -> bool:
    return (MODELS_DIR / f"{model}.param").is_file() and (MODELS_DIR / f"{model}.bin").is_file()


def check_dimensions(image_path: str) -> tuple[int, int]:
    """Return (h, w); raise ValueError if the image exceeds MAX_DIMENSION."""
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError("Gagal membaca file gambar.")
    h, w = img.shape[:2]
    if w > MAX_DIMENSION or h > MAX_DIMENSION:
        raise ValueError(
            f"Dimensi gambar terlalu besar ({w}x{h}px). "
            f"Maksimum yang diizinkan adalah {MAX_DIMENSION}x{MAX_DIMENSION}px."
        )
    return h, w


def sanitize_filename(filename: str) -> str:
    """Normalise a user filename to a safe, lowercase ascii slug."""
    name, ext = _splitext(filename)
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^\w\s-]", " ", name)
    name = re.sub(r"[\s-]+", "_", name)
    name = re.sub(r"_+", "_", name).lower().strip("_")
    if not name:
        name = "image"
    return f"{name}{ext}"


def _splitext(filename: str) -> tuple[str, str]:
    dot = filename.rfind(".")
    if dot <= 0:
        return filename, ""
    return filename[:dot], filename[dot:]


def generate_output_filename(original_filename: str, scale: float, mode: str) -> str:
    clean_name = sanitize_filename(original_filename)
    name, _ext = _splitext(clean_name)
    if mode == "noop":
        suffix = "_original"
    elif mode == "downscale":
        suffix = f"_downscaled_{str(scale).replace('.', '_')}x"
    else:  # upscale
        scale_str = f"{int(scale)}x" if scale == int(scale) else f"{scale}x"
        suffix = f"_upscaled_{scale_str}"
    return f"{name}{suffix}.png"  # always PNG output


def run_upscale(input_path: str, output_path: str, model: str, target_scale: float) -> None:
    """Upscale via realesrgan-ncnn-vulkan (always native x4) then resize to target."""
    exe = find_exe()
    if exe is None:
        raise FileNotFoundError(
            "Binary realesrgan tidak ditemukan. Taruh 'realesrgan.exe' "
            "(Windows) atau 'realesrgan-ncnn-vulkan' (Linux/macOS) di root "
            "project atau folder ./bin."
        )
    if not model_files_present(model):
        raise FileNotFoundError(
            f"File model '{model}.param' / '{model}.bin' tidak ada di {MODELS_DIR}. "
            "Unduh model Real-ESRGAN ncnn dan taruh di folder itu."
        )

    img_original = cv2.imread(input_path, cv2.IMREAD_UNCHANGED)
    if img_original is None:
        raise ValueError("Gagal membaca gambar input.")
    original_h, original_w = img_original.shape[:2]

    target_w = max(1, round(original_w * target_scale))
    target_h = max(1, round(original_h * target_scale))

    temp_output = OUTPUT_DIR / f"temp_{uuid.uuid4().hex[:10]}.png"
    cmd = [
        exe,
        "-i", input_path,
        "-o", str(temp_output),
        "-n", model,
        "-s", str(NATIVE_SCALE),  # always 4, never target_scale
        "-m", str(MODELS_DIR),
        "-t", str(TILE_SIZE),  # 0 = auto
        "-f", "png",
    ]
    print(f"CMD : {' '.join(cmd)}")
    print(f"Goal: {original_w}x{original_h} -> realesrgan 4x -> resize {target_w}x{target_h}")

    try:
        result = subprocess.run(
            cmd, cwd=str(BASE_DIR), capture_output=True, text=True, timeout=UPSCALE_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        temp_output.unlink(missing_ok=True)
        raise RuntimeError(f"realesrgan tidak merespons dalam {UPSCALE_TIMEOUT} detik.")

    if result.returncode != 0:
        temp_output.unlink(missing_ok=True)
        raise RuntimeError(f"realesrgan gagal (code {result.returncode}): {result.stderr}")

    img_4x = cv2.imread(str(temp_output), cv2.IMREAD_UNCHANGED)
    if img_4x is None:
        temp_output.unlink(missing_ok=True)
        raise RuntimeError("Gagal membaca hasil upscale dari realesrgan.")

    h4, w4 = img_4x.shape[:2]
    if w4 != target_w or h4 != target_h:
        interp = cv2.INTER_AREA if (target_w <= w4 and target_h <= h4) else cv2.INTER_LANCZOS4
        img_final = cv2.resize(img_4x, (target_w, target_h), interpolation=interp)
        cv2.imwrite(output_path, img_final)
    else:
        shutil.copy2(str(temp_output), output_path)
    temp_output.unlink(missing_ok=True)


def downscale(input_path: str, output_path: str, target_scale: float) -> None:
    """Downscale straight from the original image with OpenCV INTER_AREA."""
    img = cv2.imread(input_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError("Gagal membaca gambar.")
    h, w = img.shape[:2]
    new_w = max(1, round(w * target_scale))
    new_h = max(1, round(h * target_scale))
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    cv2.imwrite(output_path, resized)


# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------
@resolv_bp.route("/resolv/")
def index():
    return render_template(
        "resolv.html",
        models=MODEL_CHOICES,
        upscale_ready=find_exe() is not None,
    )


@resolv_bp.route("/resolv/api/process", methods=["POST"])
def process():
    if "image" not in request.files:
        return jsonify({"error": "Tidak ada file gambar yang dikirim."}), 400

    file = request.files["image"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Format file tidak didukung."}), 400

    original_filename = file.filename
    try:
        scale = float(request.form.get("scale", "1"))
    except ValueError:
        return jsonify({"error": "Nilai scale tidak valid."}), 400
    if scale < 0.25 or scale > 4.0:
        return jsonify({"error": "Scale harus antara 0.25 dan 4.0."}), 400

    model = request.form.get("model", "realesrgan-x4plus")
    if model not in MODEL_CHOICES:
        return jsonify({"error": "Model tidak dikenali."}), 400

    job_id = uuid.uuid4().hex[:10]
    ext = original_filename.rsplit(".", 1)[1].lower()
    input_path = UPLOAD_DIR / f"{job_id}_in.{ext}"
    file.save(str(input_path))

    if not input_path.exists() or input_path.stat().st_size == 0:
        return jsonify({"error": "Gagal menyimpan file."}), 500
    if input_path.stat().st_size > MAX_UPLOAD_BYTES:
        input_path.unlink(missing_ok=True)
        return jsonify({"error": "Ukuran file melebihi 25 MB."}), 400

    try:
        in_h, in_w = check_dimensions(str(input_path))
    except ValueError as exc:
        input_path.unlink(missing_ok=True)
        return jsonify({"error": str(exc)}), 400

    if abs(scale - 1.0) < 1e-9:
        mode = "noop"
    elif scale < 1.0:
        mode = "downscale"
    else:
        mode = "upscale"

    output_filename = generate_output_filename(original_filename, scale, mode)
    output_path = OUTPUT_DIR / output_filename
    started = time.time()

    try:
        if mode == "noop":
            shutil.copy2(str(input_path), str(output_path))
        elif mode == "downscale":
            downscale(str(input_path), str(output_path), scale)
        else:
            run_upscale(str(input_path), str(output_path), model, scale)
    except Exception as exc:  # noqa: BLE001 - surface any failure to the client
        output_path.unlink(missing_ok=True)
        input_path.unlink(missing_ok=True)
        return jsonify({"error": str(exc)}), 500

    elapsed = round(time.time() - started, 2)

    out_w, out_h = 0, 0
    img_out = cv2.imread(str(output_path), cv2.IMREAD_UNCHANGED)
    if img_out is not None:
        out_h, out_w = img_out.shape[:2]

    input_path.unlink(missing_ok=True)

    return jsonify(
        {
            "ok": True,
            "mode": mode,
            "scale": scale,
            "model": model if mode == "upscale" else None,
            "elapsed": elapsed,
            "input_dim": {"w": in_w, "h": in_h},
            "output_dim": {"w": out_w, "h": out_h},
            "output_url": f"/resolv/outputs/{output_filename}",
            "output_filename": output_filename,
        }
    )


@resolv_bp.route("/resolv/outputs/<path:filename>")
def serve_output(filename: str):
    return send_from_directory(str(OUTPUT_DIR), filename)


def create_standalone_app():
    """Build a minimal Flask app exposing only the RESOLV tool (for standalone use)."""
    from flask import Flask

    app = Flask(__name__, static_url_path="/static")
    app.register_blueprint(resolv_bp)
    return app


if __name__ == "__main__":
    create_standalone_app().run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
