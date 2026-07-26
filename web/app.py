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
import sys
import threading
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import torch
from flask import Flask, Response, jsonify, render_template, request

# `python web/app.py` menempatkan folder web di sys.path, bukan root repo.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from underwater_enhance.depth_pro_adapter import (
    DepthProEstimator,
    DepthProUnavailableError,
)
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
    ) -> None:
        self.source = source
        self.model_path = model_path
        self.device = device
        self.depth_every = max(1, depth_every)
        self.depth_checkpoint = depth_checkpoint
        self.lock = threading.RLock()
        self.frame_ready = threading.Condition(self.lock)
        self.running = False
        self.paused = False
        self.raw_frame: np.ndarray | None = None
        self.frozen_frame: np.ndarray | None = None
        self.latest_jpeg: bytes | None = None
        self.frame_id = 0
        self.features = {"yolo": False, "depth": False}
        self.points: list[tuple[int, int]] = []
        self.point_mode = "measurement"
        self.pending_depth = False
        self.depth_map: np.ndarray | None = None
        self.intrinsics: CameraIntrinsics | None = None
        self.calibration = ScaleCalibration()
        self.measurement = None
        self.yolo_model = None
        self.depth_model: DepthProEstimator | None = None
        self.logs: deque[str] = deque(maxlen=40)
        self.error: str | None = None
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
            self.depth_model = DepthProEstimator(self.device, self.depth_checkpoint)
            self.log("Depth Pro model loaded.")
            return True
        except DepthProUnavailableError as exc:
            self.error = str(exc)
            self.log(f"Depth Pro unavailable: {exc}")
            return False

    def _run_depth_for_frozen(self) -> None:
        with self.lock:
            frame = None if self.frozen_frame is None else self.frozen_frame.copy()
        if frame is None or not self._ensure_depth():
            return
        started = time.perf_counter()
        try:
            prediction = self.depth_model.infer(frame)
            intrinsics = default_intrinsics(
                frame.shape[1], frame.shape[0], prediction.focal_length_px
            )
            with self.lock:
                self.depth_map = prediction.depth_m
                self.intrinsics = intrinsics
                if len(self.points) == 2:
                    if self.point_mode == "calibration":
                        known = self._pending_known_length
                        self.calibration = calibration_from_reference(
                            self.points[0],
                            self.points[1],
                            known,
                            self.depth_map,
                            self.intrinsics,
                            source="REFERENCE_SCALED",
                        )
                        self.measurement = None
                        self.log(
                            f"Reference calibrated: scale={self.calibration.scale:.4f}, "
                            f"reference={known:.3f}m"
                        )
                    else:
                        self.measurement = measure_distance(
                            self.points[0],
                            self.points[1],
                            self.depth_map,
                            self.intrinsics,
                            self.calibration,
                        )
                        self.log(
                            f"Measurement {self.measurement.distance_m:.3f}m ± "
                            f"{self.measurement.uncertainty_m:.3f}m "
                            f"[{self.measurement.status}]"
                        )
        except Exception as exc:  # noqa: BLE001 - keep worker alive on model failure
            self.error = f"Depth inference error: {exc}"
            self.log(self.error)
        finally:
            with self.lock:
                self.pending_depth = False
            self.log(f"Depth inference {time.perf_counter() - started:.2f}s")

    def _annotate(self, frame: np.ndarray) -> np.ndarray:
        canvas = frame.copy()
        with self.lock:
            yolo_enabled = self.features["yolo"]
            points = list(self.points)
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

        for point in points:
            cv2.circle(canvas, point, 7, (0, 255, 255), -1, cv2.LINE_AA)
        if len(points) == 2:
            cv2.line(canvas, points[0], points[1], (0, 255, 255), 2, cv2.LINE_AA)
        if measurement is not None and len(points) == 2:
            midpoint = ((points[0][0] + points[1][0]) // 2, (points[0][1] + points[1][1]) // 2)
            text = (
                f"{measurement.distance_m:.3f} m +/- {measurement.uncertainty_m:.3f} m "
                f"[{measurement.status}]"
            )
            cv2.putText(canvas, text, midpoint, cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 4)
            cv2.putText(canvas, text, midpoint, cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
        else:
            label = "CALIBRATION: click 2 reference points" if mode == "calibration" else "MEASUREMENT: click 2 points"
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
                self.frozen_frame = self.raw_frame.copy()
                self.paused = True
                self.points = []
                self.measurement = None
            height, width = self.frozen_frame.shape[:2]
            point = (
                int(np.clip(x_norm, 0, 1) * (width - 1)),
                int(np.clip(y_norm, 0, 1) * (height - 1)),
            )
            if len(self.points) >= 2:
                self.points = []
                self.measurement = None
            self.points.append(point)
            if len(self.points) == 2:
                self.pending_depth = True
            self.log(f"Point {len(self.points)}: {point}")

    def configure_mode(self, mode: str, known_length_m: float | None = None) -> None:
        if mode not in ("measurement", "calibration"):
            raise ValueError("Mode harus measurement atau calibration.")
        if mode == "calibration" and (known_length_m is None or known_length_m <= 0):
            raise ValueError("Calibration membutuhkan panjang referensi meter > 0.")
        with self.lock:
            self.point_mode = mode
            self._pending_known_length = known_length_m
            self.points = []
            self.measurement = None
            self.paused = False
        self.log(f"Mode: {mode}")

    def resume(self) -> None:
        with self.lock:
            self.paused = False
            self.points = []
            self.measurement = None
            self.pending_depth = False
        self.log("Stream resumed.")

    def state(self) -> dict:
        with self.lock:
            vram = 0.0
            if torch.cuda.is_available():
                vram = torch.cuda.memory_allocated() / 1024**2
            return {
                "features": self.features,
                "paused": self.paused,
                "points": self.points,
                "mode": self.point_mode,
                "calibration": {
                    "scale": self.calibration.scale,
                    "source": self.calibration.source,
                    "known_length_m": self.calibration.known_length_m,
                },
                "measurement": None if self.measurement is None else {
                    "distance_m": self.measurement.distance_m,
                    "uncertainty_m": self.measurement.uncertainty_m,
                    "status": self.measurement.status,
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
            engine.configure_mode(data["mode"], data.get("known_length_m"))
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

    @app.post("/api/resume")
    def resume():
        engine.resume()
        return jsonify(engine.state())

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
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    engine = InspectionEngine(
        args.source,
        args.model,
        args.device,
        args.depth_every,
        args.depth_checkpoint,
    )
    engine.start()
    app = create_app(engine)
    try:
        app.run(host="127.0.0.1", port=args.port, debug=False, threaded=True)
    finally:
        engine.stop()


if __name__ == "__main__":
    main()
