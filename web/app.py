"""Flask Vision Inspection Console.

Jalankan:
  python web/app.py --source "D:\\arcgiz\\video 1.mp4" --model best.pt

Depth Pro hanya di-load saat toggle Depth dinyalakan. Klik dua titik pada
canvas membekukan frame agar depth dan titik selalu berasal dari frame yang
sama. Mode calibration memakai dua titik pada diameter pipa atau dua titik
laser dengan jarak diketahui; mode measurement memakai scale tersebut.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import threading
import time
import uuid
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import torch
from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    send_from_directory,
)

# `python web/app.py` menempatkan folder web di sys.path, bukan root repo.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from underwater_enhance.depth_estimator import DEPTH_BACKENDS, create_depth_estimator
from underwater_enhance.depth_pro_adapter import DepthProUnavailableError
from underwater_enhance.measurement import (
    CameraIntrinsics,
    ScaleCalibration,
    calibration_from_reference,
    default_intrinsics,
    measure_distance,
)


class InspectionEngine:
    """Single-worker video pipeline; mencegah model dimuat per browser client."""

    def __init__(
        self,
        source: str,
        model_path: str | None,
        device: str,
        depth_every: int,
        depth_checkpoint: str | None = None,
        depth_backend: str = "depth_anything3",
        depth_model_id: str | None = None,
        depth_process_res: int = 504,
        gallery_dir: str = "web/data/gallery",
    ) -> None:
        self.source = source
        self.model_path = model_path
        self.device = device
        self.depth_every = max(1, depth_every)
        self.depth_checkpoint = depth_checkpoint
        self.depth_backend = depth_backend
        self.depth_model_id = depth_model_id
        self.depth_process_res = depth_process_res
        self.gallery_dir = Path(gallery_dir)
        self.gallery_dir.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.frame_ready = threading.Condition(self.lock)
        self.running = False
        self.paused = False
        self.raw_frame: np.ndarray | None = None
        self.frozen_frame: np.ndarray | None = None
        self.frozen_frame_id: int | None = None
        self.latest_jpeg: bytes | None = None
        self.frame_id = 0
        self.features = {"yolo": False, "depth": False}
        self.calibration_points: list[tuple[int, int]] = []
        self.measurement_points: list[tuple[int, int]] = []
        self.point_mode = "measurement"
        self.pending_depth = False
        self.pending_action: str | None = None
        self.depth_map: np.ndarray | None = None
        self.intrinsics: CameraIntrinsics | None = None
        self.calibration = ScaleCalibration()
        self.calibration_inference_state = "IDLE"
        self.calibration_inference_message = "Belum ada calibration inference."
        self.measurement = None
        self.yolo_model = None
        self.depth_model: object | None = None
        self.logs: deque[str] = deque(maxlen=40)
        self.error: str | None = None
        self._pending_known_length_m: float | None = None
        self._thread: threading.Thread | None = None

    def log(self, text: str) -> None:
        with self.lock:
            self.logs.appendleft(f"{time.strftime('%H:%M:%S')} {text}")

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run, name="vision-worker", daemon=True)
        self._thread.start()
        self.log("Video worker started.")

    def stop(self) -> None:
        self.running = False
        if self._thread:
            self._thread.join(timeout=3)
        self._unload_models()

    def _unload_models(self) -> None:
        with self.lock:
            self.yolo_model = None
            if self.depth_model is not None:
                self.depth_model.close()
                self.depth_model = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _ensure_yolo(self) -> bool:
        if self.yolo_model is not None:
            return True
        if not self.model_path or not Path(self.model_path).is_file():
            self.error = "YOLO model path tidak tersedia."
            return False
        try:
            from ultralytics import YOLO

            self.yolo_model = YOLO(self.model_path)
            self.log("YOLO model loaded.")
            return True
        except Exception as exc:  # noqa: BLE001 - expose model loading diagnostics in UI
            self.error = f"YOLO load error: {exc}"
            return False

    def _ensure_depth(self) -> bool:
        if self.depth_model is not None:
            return True
        try:
            self.depth_model = create_depth_estimator(
                self.depth_backend,
                self.device,
                checkpoint=self.depth_checkpoint,
                model_id=self.depth_model_id,
                process_res=self.depth_process_res,
            )
            self.error = None
            self.log(f"Depth backend loaded: {self.depth_backend}.")
            return True
        except DepthProUnavailableError as exc:
            self.error = str(exc)
            self.log(f"Depth Pro unavailable: {exc}")
            return False

    def _run_depth_for_frozen(self) -> None:
        with self.lock:
            frame = None if self.frozen_frame is None else self.frozen_frame.copy()
            action = self.pending_action
            points = (
                list(self.calibration_points)
                if action == "calibration"
                else list(self.measurement_points)
            )
            known_length_m = self._pending_known_length_m
            frozen_frame_id = self.frozen_frame_id
        if frame is None:
            with self.lock:
                self.pending_depth = False
                self.pending_action = None
            return
        if not self._ensure_depth():
            # Jangan retry pada setiap iterasi paused; error backend dan log
            # calibration harus tetap terbaca sampai operator mencoba lagi.
            with self.lock:
                self.pending_depth = False
                self.pending_action = None
                if action == "calibration":
                    self.calibration_inference_state = "FAILED"
                    self.calibration_inference_message = self.error or "Depth backend tidak tersedia."
            return
        started = time.perf_counter()
        try:
            if action == "calibration":
                with self.lock:
                    self.calibration_inference_state = "RUNNING"
                    self.calibration_inference_message = "Depth inference sedang berjalan pada frame beku."
            prediction = self.depth_model.infer(frame)
            intrinsics = default_intrinsics(
                frame.shape[1], frame.shape[0], prediction.focal_length_px
            )
            with self.lock:
                self.depth_map = prediction.depth_m
                self.intrinsics = intrinsics
                if len(points) == 2:
                    if action == "calibration":
                        if known_length_m is None:
                            raise ValueError("Panjang calibration belum disimpan.")
                        self.calibration = calibration_from_reference(
                            points[0],
                            points[1],
                            known_length_m,
                            self.depth_map,
                            self.intrinsics,
                            source="REFERENCE_SCALED",
                            frame_id=frozen_frame_id,
                            backend_signature=prediction.model_id,
                            intrinsics_source=prediction.intrinsics_source,
                        )
                        self.measurement = None
                        self.calibration_inference_state = "COMPLETE"
                        self.calibration_inference_message = (
                            f"Depth reference={self.calibration.raw_reference_distance_m:.4f} m → "
                            f"physical={known_length_m * 100:.2f} cm; "
                            f"scale={self.calibration.scale:.4f}x"
                        )
                        self.log(
                            f"Calibration inference COMPLETE: depth reference="
                            f"{self.calibration.raw_reference_distance_m:.4f} m → "
                            f"physical={known_length_m * 100:.2f} cm; "
                            f"scale={self.calibration.scale:.4f}x, frame={frozen_frame_id}"
                        )
                    elif action == "measurement":
                        self.measurement = measure_distance(
                            points[0],
                            points[1],
                            self.depth_map,
                            self.intrinsics,
                            self.calibration,
                            frame_id=frozen_frame_id,
                        )
                        self.log(
                            f"Measurement {self.measurement.distance_m:.3f}m ± "
                            f"{self.measurement.uncertainty_m:.3f}m "
                            f"[{self.measurement.validity}]"
                        )
        except Exception as exc:  # noqa: BLE001 - keep worker alive on model failure
            self.error = f"Depth inference error: {exc}"
            if action == "calibration":
                self.calibration_inference_state = "FAILED"
                self.calibration_inference_message = self.error
            self.log(self.error)
        finally:
            with self.lock:
                self.pending_depth = False
                self.pending_action = None
            self.log(f"Depth inference {time.perf_counter() - started:.2f}s")

    def _annotate(self, frame: np.ndarray) -> np.ndarray:
        canvas = frame.copy()
        with self.lock:
            yolo_enabled = self.features["yolo"]
            calibration_points = list(self.calibration_points)
            measurement_points = list(self.measurement_points)
            measurement = self.measurement
            mode = self.point_mode
        if yolo_enabled and self._ensure_yolo():
            try:
                result = self.yolo_model.predict(
                    canvas, conf=0.7, device=self.device, verbose=False
                )[0]
                canvas = result.plot(img=canvas)
            except Exception as exc:  # noqa: BLE001 - keep stream alive on model failure
                self.error = f"YOLO inference error: {exc}"

        # Biru: titik khusus calibration diameter pipa/laser.
        for point in calibration_points:
            cv2.circle(canvas, point, 7, (255, 120, 0), -1, cv2.LINE_AA)
        if len(calibration_points) == 2:
            cv2.line(
                canvas, calibration_points[0], calibration_points[1],
                (255, 120, 0), 2, cv2.LINE_AA,
            )
            cv2.putText(
                canvas, "CALIBRATION REFERENCE (BLUE)", (20, 65),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 120, 0), 2,
            )
            if self.calibration_inference_state == "COMPLETE":
                cal_text = (
                    f"CAL INFERENCE: {self.calibration.raw_reference_distance_m:.3f}m "
                    f"-> {self.calibration.known_length_m * 100:.2f}cm "
                    f"(scale {self.calibration.scale:.3f}x)"
                )
                cv2.putText(
                    canvas, cal_text, (20, 90), cv2.FONT_HERSHEY_SIMPLEX,
                    0.52, (0, 255, 0), 2,
                )

        # Kuning: titik pengukuran setelah calibration tersimpan.
        for point in measurement_points:
            cv2.circle(canvas, point, 7, (0, 255, 255), -1, cv2.LINE_AA)
        if len(measurement_points) == 2:
            cv2.line(
                canvas, measurement_points[0], measurement_points[1],
                (0, 255, 255), 2, cv2.LINE_AA,
            )
        if measurement is not None and len(measurement_points) == 2:
            midpoint = (
                (measurement_points[0][0] + measurement_points[1][0]) // 2,
                (measurement_points[0][1] + measurement_points[1][1]) // 2,
            )
            text = (
                f"{measurement.distance_m:.3f} m +/- {measurement.uncertainty_m:.3f} m "
                f"[{measurement.validity}]"
            )
            cv2.putText(canvas, text, midpoint, cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 4)
            cv2.putText(canvas, text, midpoint, cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
            if measurement.warnings:
                warning = measurement.warnings[0]
                cv2.putText(
                    canvas, warning, (20, 90), cv2.FONT_HERSHEY_SIMPLEX,
                    0.52, (0, 165, 255), 2,
                )
        else:
            label = (
                "CALIBRATION: click 2 BLUE reference points, then Save calibration"
                if mode == "calibration"
                else "MEASUREMENT: click 2 YELLOW points"
            )
            cv2.putText(canvas, label, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 4)
            cv2.putText(canvas, label, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
        return canvas

    def _publish(self, frame: np.ndarray) -> None:
        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ok:
            return
        with self.frame_ready:
            self.latest_jpeg = encoded.tobytes()
            self.frame_ready.notify_all()

    def _run(self) -> None:
        cap = cv2.VideoCapture(int(self.source) if self.source.isdigit() else self.source)
        if not cap.isOpened():
            self.error = f"Cannot open source: {self.source}"
            return
        try:
            while self.running:
                with self.lock:
                    paused = self.paused
                    pending = self.pending_depth
                    frozen = None if self.frozen_frame is None else self.frozen_frame.copy()
                if paused:
                    if pending:
                        self._run_depth_for_frozen()
                    if frozen is not None:
                        self._publish(self._annotate(frozen))
                    time.sleep(0.03)
                    continue

                ok, frame = cap.read()
                if not ok:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                with self.lock:
                    self.raw_frame = frame.copy()
                    self.frame_id += 1
                    depth_enabled = self.features["depth"]
                # Depth keyframe preview is intentionally not run continuously;
                # it will run when a user freezes/clicks a measurement frame.
                if depth_enabled and self.frame_id % self.depth_every == 0:
                    self.log("Depth waiting for point selection (keyframe policy).")
                self._publish(self._annotate(frame))
        finally:
            cap.release()

    def set_feature(self, name: str, enabled: bool) -> None:
        if name not in self.features:
            raise ValueError("Feature tidak dikenal.")
        with self.lock:
            self.features[name] = enabled
        if not enabled:
            if name == "yolo":
                self.yolo_model = None
            if name == "depth" and self.depth_model is not None:
                self.depth_model.close()
                self.depth_model = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        self.log(f"{name.upper()} {'ON' if enabled else 'OFF'}")

    def add_point(self, x_norm: float, y_norm: float) -> None:
        with self.lock:
            if self.raw_frame is None:
                raise ValueError("Belum ada frame video.")
            if not self.paused:
                self._freeze_locked(clear_points=True)
            height, width = self.frozen_frame.shape[:2]
            point = (
                int(np.clip(x_norm, 0, 1) * (width - 1)),
                int(np.clip(y_norm, 0, 1) * (height - 1)),
            )
            points = (
                self.calibration_points
                if self.point_mode == "calibration"
                else self.measurement_points
            )
            if len(points) >= 2:
                points.clear()
                self.measurement = None
            points.append(point)
            if self.point_mode == "measurement" and len(points) == 2:
                self.pending_action = "measurement"
                self.pending_depth = True
            color = "BLUE calibration" if self.point_mode == "calibration" else "YELLOW measurement"
            self.log(f"{color} point {len(points)}: {point}")

    def _freeze_locked(self, *, clear_points: bool) -> None:
        if self.raw_frame is None:
            raise ValueError("Belum ada frame video.")
        self.frozen_frame = self.raw_frame.copy()
        self.frozen_frame_id = self.frame_id
        self.paused = True
        self.pending_depth = False
        self.pending_action = None
        self.measurement = None
        if clear_points:
            self.calibration_points = []
            self.measurement_points = []
        self.log("Frame frozen.")

    def freeze(self) -> None:
        """Pause eksplisit tanpa menempatkan titik pengukuran."""
        with self.lock:
            self._freeze_locked(clear_points=True)

    def clear_points(self) -> None:
        with self.lock:
            self.calibration_points = []
            self.measurement_points = []
            self.measurement = None
            self.pending_depth = False
            self.pending_action = None
        self.log("Points cleared.")

    def configure_mode(self, mode: str) -> None:
        if mode not in ("measurement", "calibration"):
            raise ValueError("Mode harus measurement atau calibration.")
        with self.lock:
            self.point_mode = mode
            if mode == "calibration":
                self.calibration_points = []
            else:
                self.measurement_points = []
            self.measurement = None
        self.log(f"Mode: {mode}")

    def save_calibration_cm(self, length_cm: float) -> None:
        """Simpan diameter pipa/jarak laser setelah dua titik biru dipilih."""
        if length_cm <= 0:
            raise ValueError("Nilai calibration harus lebih besar dari 0 cm.")
        with self.lock:
            if not self.paused:
                raise ValueError("Freeze frame dahulu sebelum menyimpan calibration.")
            if len(self.calibration_points) != 2:
                raise ValueError("Pilih tepat dua titik biru calibration terlebih dahulu.")
            self._pending_known_length_m = length_cm / 100.0
            self.pending_action = "calibration"
            self.pending_depth = True
            self.calibration_inference_state = "QUEUED"
            self.calibration_inference_message = (
                f"Queued: infer depth untuk reference {length_cm:.2f} cm pada frame beku."
            )
        self.log(
            f"Calibration saved: reference {length_cm:.2f} cm "
            f"({length_cm / 100.0:.4f} m); depth inference queued."
        )

    def resume(self) -> None:
        with self.lock:
            had_calibration = self.calibration.source == "REFERENCE_SCALED"
            self.paused = False
            self.calibration_points = []
            self.measurement_points = []
            self.measurement = None
            self.pending_depth = False
            self.pending_action = None
            self.frozen_frame = None
            self.frozen_frame_id = None
            # Monocular reference scaling berubah dengan scene/focal/depth.
            # Jangan biarkan hasil calibration lama dipakai lintas frame.
            self.calibration = ScaleCalibration()
            self.calibration_inference_state = "IDLE"
            self.calibration_inference_message = "Calibration dihapus setelah Resume."
        self.log("Stream resumed.")
        if had_calibration:
            self.log("Reference calibration invalidated after resume; recalibrate on next frozen frame.")

    def save_snapshot(self) -> dict:
        """Persist frozen/current high-resolution frame beserta measurement JSON."""
        with self.lock:
            frame = self.frozen_frame if self.paused else self.raw_frame
            if frame is None:
                raise ValueError("Belum ada frame untuk disimpan.")
            snapshot = frame.copy()
            measurement = None if self.measurement is None else {
                "distance_m": self.measurement.distance_m,
                "uncertainty_m": self.measurement.uncertainty_m,
                "status": self.measurement.status,
                "validity": self.measurement.validity,
                "warnings": self.measurement.warnings,
            }
            metadata = {
                "id": uuid.uuid4().hex,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "frame_id": self.frame_id,
                "measurement": measurement,
                "calibration": {
                    "scale": self.calibration.scale,
                    "source": self.calibration.source,
                    "known_length_m": self.calibration.known_length_m,
                    "raw_reference_distance_m": self.calibration.raw_reference_distance_m,
                    "frame_id": self.calibration.frame_id,
                    "backend_signature": self.calibration.backend_signature,
                    "intrinsics_source": self.calibration.intrinsics_source,
                    "inference_state": self.calibration_inference_state,
                    "inference_message": self.calibration_inference_message,
                },
            }
        image_name = f"{metadata['id']}.jpg"
        metadata["image"] = image_name
        cv2.imwrite(str(self.gallery_dir / image_name), snapshot)
        (self.gallery_dir / f"{metadata['id']}.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )
        self.log(f"Snapshot saved: {image_name}")
        return metadata

    def gallery_entries(self) -> list[dict]:
        entries = []
        for path in sorted(self.gallery_dir.glob("*.json"), reverse=True):
            try:
                entries.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
        return entries

    def set_context(self, context: str) -> None:
        """Gallery membebaskan model live agar RTX 3070 tidak OOM."""
        if context not in ("live", "gallery"):
            raise ValueError("Context harus live atau gallery.")
        if context == "gallery":
            self.set_feature("yolo", False)
            self.set_feature("depth", False)
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
            self.log("Gallery context active; live models unloaded.")

    def state(self) -> dict:
        with self.lock:
            vram = 0.0
            if torch.cuda.is_available():
                vram = torch.cuda.memory_allocated() / 1024**2
            return {
                "features": self.features,
                "depth_backend": self.depth_backend,
                "paused": self.paused,
                "calibration_points": self.calibration_points,
                "measurement_points": self.measurement_points,
                "mode": self.point_mode,
                "calibration": {
                    "scale": self.calibration.scale,
                    "source": self.calibration.source,
                    "known_length_m": self.calibration.known_length_m,
                    "raw_reference_distance_m": self.calibration.raw_reference_distance_m,
                    "frame_id": self.calibration.frame_id,
                    "backend_signature": self.calibration.backend_signature,
                    "intrinsics_source": self.calibration.intrinsics_source,
                    "inference_state": self.calibration_inference_state,
                    "inference_message": self.calibration_inference_message,
                },
                "measurement": None if self.measurement is None else {
                    "distance_m": self.measurement.distance_m,
                    "uncertainty_m": self.measurement.uncertainty_m,
                    "status": self.measurement.status,
                    "validity": self.measurement.validity,
                    "warnings": self.measurement.warnings,
                    "depth_a_m": self.measurement.depth_a_m,
                    "depth_b_m": self.measurement.depth_b_m,
                },
                "vram_mb": round(vram, 1),
                "error": self.error,
                "logs": list(self.logs),
            }


def create_app(engine: InspectionEngine) -> Flask:
    app = Flask(__name__, template_folder="templates")

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/live")
    def live():
        return render_template("index.html")

    @app.get("/gallery")
    def gallery():
        engine.set_context("gallery")
        return render_template("gallery.html")

    @app.get("/video_feed")
    def video_feed():
        def generate():
            while engine.running:
                with engine.frame_ready:
                    engine.frame_ready.wait_for(lambda: engine.latest_jpeg is not None, timeout=1)
                    frame = engine.latest_jpeg
                if frame:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.get("/api/state")
    def state():
        return jsonify(engine.state())

    @app.post("/api/feature")
    def feature():
        data = request.get_json(force=True)
        try:
            engine.set_feature(data["name"], bool(data["enabled"]))
            return jsonify(engine.state())
        except (KeyError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/api/mode")
    def mode():
        data = request.get_json(force=True)
        try:
            engine.configure_mode(data["mode"])
            return jsonify(engine.state())
        except (KeyError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/api/point")
    def point():
        data = request.get_json(force=True)
        try:
            engine.add_point(float(data["x_norm"]), float(data["y_norm"]))
            return jsonify(engine.state())
        except (KeyError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/api/calibration")
    def calibration():
        data = request.get_json(force=True)
        try:
            engine.save_calibration_cm(float(data["length_cm"]))
            return jsonify(engine.state())
        except (KeyError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/api/resume")
    def resume():
        engine.resume()
        return jsonify(engine.state())

    @app.post("/api/freeze")
    def freeze():
        try:
            engine.freeze()
            return jsonify(engine.state())
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/api/clear-points")
    def clear_points():
        engine.clear_points()
        return jsonify(engine.state())

    @app.post("/api/snapshot")
    def snapshot():
        try:
            return jsonify(engine.save_snapshot())
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.get("/api/gallery")
    def gallery_api():
        return jsonify(engine.gallery_entries())

    @app.get("/api/gallery/<entry_id>/image")
    def gallery_image(entry_id: str):
        return send_from_directory(engine.gallery_dir, f"{entry_id}.jpg")

    @app.post("/api/context")
    def context():
        data = request.get_json(force=True)
        try:
            engine.set_context(data["context"])
            return jsonify(engine.state())
        except (KeyError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400

    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Path video atau indeks kamera")
    parser.add_argument("--model", help="Path best.pt untuk toggle YOLO")
    parser.add_argument("--device", default="0", help="YOLO/Depth device, default GPU 0")
    parser.add_argument("--depth-every", type=int, default=15)
    parser.add_argument(
        "--depth-checkpoint",
        default="checkpoints/depth_pro.pt",
        help="Path depth_pro.pt hasil download resmi Apple",
    )
    parser.add_argument(
        "--depth-backend",
        choices=DEPTH_BACKENDS,
        default="depth_anything3",
        help="Backend depth (default: depth_anything3)",
    )
    parser.add_argument(
        "--depth-model-id",
        default="depth-anything/DA3METRIC-LARGE",
        help="Hugging Face model id untuk DA3 metric",
    )
    parser.add_argument(
        "--depth-process-res",
        type=int,
        default=504,
        help="Resolusi inference DA3 pada frozen frame (default: 504)",
    )
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    engine = InspectionEngine(
        args.source,
        args.model,
        args.device,
        args.depth_every,
        args.depth_checkpoint,
        args.depth_backend,
        args.depth_model_id,
        args.depth_process_res,
    )
    engine.start()
    app = create_app(engine)
    try:
        app.run(host="127.0.0.1", port=args.port, debug=False, threaded=True)
    finally:
        engine.stop()


if __name__ == "__main__":
    main()
