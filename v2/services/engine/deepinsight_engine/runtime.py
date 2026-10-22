"""Mengikat ring buffer, ModelManager, cache, dan watchdog pada satu sesi engine."""

from __future__ import annotations

import contextlib
import json
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

from .core.config import Settings
from .core.errors import EngineError
from .core.ids import uuid7
from .diagnostics import LiveStatus, probe_gpu
from .gpu.cache import CacheManager
from .gpu.manager import ModelManager
from .gpu.probe import VramProbe
from .gpu.watchdog import Watchdog
from .video.capture import CaptureLoop
from .video.evidence import store_png
from .video.file_source import open_live, read_file
from .video.frames import RingBuffer, StoredFrame
from .video.live_infer import LiveInfer, publish_allowed
from .video.marks import store_jpeg
from .video.pipeline import FramePipeline
from .video.quality import configured, turbidity_level
from .video.synthetic import gradient_bgr


class Runtime:
    def __init__(
        self,
        settings: Settings,
        models_dir: Path,
        data_dir: Path,
        on_error: Callable[[str, str | None], None],
        probe: VramProbe,
    ) -> None:
        perf = settings.thresholds.performance
        self._settings = settings
        self._on_error = on_error
        self._evidence = data_dir / "evidence"
        self._serial = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lost: str | None = None
        self._sent_warning: str | None = None
        self._lock = threading.RLock()
        self._audit: Callable[[str, str, str, str], None] = _noop_audit
        self._capture = CaptureLoop(self._ingest, settings.thresholds.video.fps)
        self._marks = data_dir / "marks"
        self._uploads = data_dir / "uploads"
        self._snaps = data_dir / "snapshots"
        self._assist = data_dir / "assist"
        self._transform_lock = threading.Lock()
        self._transform: dict[str, object] = {}
        self._assist_lock = threading.Lock()
        self._bake_lock = threading.Lock()
        self._bake_token = 0
        self._bake: dict[str, object] = {}
        self._vision: dict[str, object] = {}
        self._live_infer = LiveInfer(self._infer_later)
        self.models = ModelManager(
            settings.models,
            models_dir,
            settings.aquaclear.presets,
            settings.aquaclear.default,
            probe,
            perf.unload_timeout_s,
            perf.load_timeout_s,
            perf.vram_baseline_tolerance_mb,
            on_error,
            hydro=settings.hydrodetect,
            spatial=settings.spatialsight,
            display_max_side=settings.thresholds.video.display_max_side,
            vram_budget_mb=perf.vram_budget_mb,
            gpu_max_pct=perf.gpu_max_pct,
        )
        self.cache = CacheManager(data_dir / "cache", settings.thresholds.cache.max_mb)
        self.pipeline = FramePipeline(
            RingBuffer(settings.thresholds.video.ring_buffer_s),
            settings.thresholds.video,
            self._enhance,
        )
        self.watchdog = Watchdog(perf, probe, self._display_fps, time.monotonic)

    def start(self) -> None:
        from .gpu.tensorflow_mem import enable_memory_growth

        enable_memory_growth()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="di-watchdog", daemon=True)
        self._thread.start()
        self._open_configured_source()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
        self._capture.stop()
        self.models.close()

    def bind_audit(self, audit: Callable[[str, str, str, str], None]) -> None:
        self._audit = audit

    def poll(self) -> None:
        with self._lock:
            lost = self.pipeline.observe(time.monotonic())
        if lost and lost != self._lost:
            self._on_error(lost, "sinyal video")
        self._lost = lost
        warning = self.watchdog.tick()
        if warning and warning != self._sent_warning:
            self._on_error(warning, self.watchdog.detail)
            self._audit("performance_warning", "watchdog", warning, self.watchdog.detail or "")
        self._sent_warning = warning

    def status(self) -> LiveStatus:
        now = time.monotonic()
        with self._lock:
            return LiveStatus(
                model_active=self.models.active,
                model_state=self.models.state,
                workers=self.models.workers,
                video_state=self.pipeline.state,
                fps_display=self.pipeline.fps("display", now),
                fps_inference=self.pipeline.fps("infer", now),
                frame_count=len(self.pipeline.ring),
                cache_mb=self.cache.used_mb(),
                performance_warning=self.watchdog.warning,
                performance_detail=self.watchdog.detail,
            )

    def switch(self, name: str, preset: str | None) -> None:
        self._live_infer.cancel()
        with self._lock:
            self._vision = {}
        self.models.switch(name, preset)

    def push_synthetic(self, count: int, width: int, height: int) -> list[str]:
        self._check_geometry(count, width, height)
        return self._push_many(_synthetic_frames(count, width, height, self._settings))

    def push_file(self, path: Path) -> list[str]:
        video = self._settings.thresholds.video
        frames = read_file(path, video.fps * int(video.ring_buffer_s))
        now = time.monotonic()
        stored = [StoredFrame(uuid7(), now, width, height, bgr) for width, height, bgr in frames]
        return self._push_many(stored)

    def save_upload(self, suffix: str, payload: bytes) -> Path:
        self._uploads.mkdir(parents=True, exist_ok=True)
        target = self._uploads / f"{uuid7()}{suffix}"
        target.write_bytes(payload)
        return target

    def open_device(
        self,
        kind: str,
        path: str | None = None,
        device_index: int | None = None,
        rtsp_url: str | None = None,
    ) -> None:
        capture = open_live(kind, path, device_index, rtsp_url)
        with self._lock:
            if self.pipeline.state == "not_configured":
                self.pipeline.state = "connecting"
        self._capture.start(capture)

    def freeze(self, frame_id: str, session: str) -> dict[str, object]:
        with self._lock:
            self._reject_lost(frame_id)
            frame = self.pipeline.ring.get(frame_id)
            if frame is None:
                raise EngineError("VID-002", frame_id)
            if not (self._evidence / f"{frame.frame_id}.png").is_file():
                self._serial += 1
            preset = self.models.preset_name if self.models.active == "aquaclear" else None
            body = store_png(self._evidence, frame, session, max(self._serial, 1), preset)
            return self._named_snap(frame, body)

    def snap_bundle(self, file_id: str) -> dict[str, object] | None:
        from .measure.snapfile import bundle

        found = bundle(self._snaps, file_id)
        if found is None:
            return None
        with self._transform_lock:
            current = dict(self._transform)
        if current.get("file_id") == found["file_id"]:
            found["running"] = bool(current.get("running"))
            found["current"] = current.get("current")
            found["note"] = str(current.get("note") or "")
        return found

    def begin_transform(self, file_id: str) -> dict[str, object]:
        """Hitung AquaClear, HydroDetect, lalu SpatialSight. VRAM dikosongkan tiap model."""
        found = self.snap_bundle(file_id)
        if found is None:
            raise EngineError("API-003", file_id)
        with self._transform_lock:
            current = dict(self._transform)
            if current.get("file_id") == found["file_id"] and current.get("running"):
                return current
            self._transform = {
                "file_id": found["file_id"],
                "stamp": found["stamp"],
                "frame_id": found["frame_id"],
                "running": True,
                "current": "aquaclear",
                "note": "",
                "snap": found["snap"],
                "aqua": found["aqua"],
                "hydro": found["hydro"],
                "spatial": found["spatial"],
                "ready": found["ready"],
            }
            started = dict(self._transform)
        threading.Thread(
            target=self._transform_worker,
            args=(str(found["file_id"]), str(found["stamp"]), str(found["frame_id"])),
            name="di-transform",
            daemon=True,
        ).start()
        return started

    def transform_status(self, file_id: str) -> dict[str, object]:
        found = self.snap_bundle(file_id)
        if found is None:
            raise EngineError("API-003", file_id)
        with self._transform_lock:
            current = dict(self._transform)
        if current.get("file_id") != found["file_id"]:
            found["running"] = False
            found["current"] = None
            found["note"] = ""
            return found
        current["aqua"] = found["aqua"]
        current["hydro"] = found["hydro"]
        current["spatial"] = found["spatial"]
        current["ready"] = found["ready"]
        return current

    def _named_snap(self, frame: StoredFrame, body: dict[str, object]) -> dict[str, object]:
        from .measure.snapfile import write_snap

        video = self._settings.thresholds.video
        file_id, stamp = write_snap(
            self._snaps,
            frame,
            body,
            video.display_max_side,
            video.display_jpeg_quality,
        )
        body["file_id"] = file_id
        body["stamp"] = stamp
        path = body.get("path")
        if isinstance(path, str) and path:
            Path(path).with_suffix(".json").write_text(json.dumps(body), encoding="utf-8")
        return body

    def _transform_worker(self, file_id: str, stamp: str, frame_id: str) -> None:
        from .measure.canvas_assist import assist_frame
        from .measure.snapfile import product_jpeg, write_product
        from .video.decode import decode_png

        steps = (
            ("aquaclear", "AquaClear"),
            ("hydrodetect", "HydroDetect"),
            ("spatialsight", "SpatialSight"),
        )
        notes: list[str] = []
        path = self._evidence / f"{frame_id}.png"
        try:
            width, height, raw = decode_png(path.read_bytes())
        except (OSError, EngineError) as exc:
            self._finish_transform(file_id, str(exc))
            return
        preset = self._settings.aquaclear.default
        for view, label in steps:
            self._publish_transform(file_id, True, view, " ".join(notes))
            step = self._transform_one(
                view,
                label,
                stamp,
                frame_id,
                raw,
                width,
                height,
                preset,
                assist_frame,
                product_jpeg,
                write_product,
            )
            if step:
                notes.append(step)
        with self._assist_lock, contextlib.suppress(EngineError):
            self.models.switch("optical")
        self._finish_transform(file_id, " ".join(notes))

    def _transform_one(
        self,
        view: str,
        label: str,
        stamp: str,
        frame_id: str,
        raw: bytes,
        width: int,
        height: int,
        preset: str,
        assist_frame: Callable[..., dict[str, object]],
        product_jpeg: Callable[..., bytes | None],
        write_product: Callable[..., str],
    ) -> str:
        try:
            with self._assist_lock:
                self.models.switch(view, preset if view == "aquaclear" else None)
                row = assist_frame(self.models, self._settings, frame_id, raw, width, height, view)
                jpeg = product_jpeg(row, raw, width, height)
            if row.get("ready") and jpeg is not None:
                write_product(
                    self._snaps,
                    stamp,
                    view,
                    frame_id,
                    jpeg,
                    str(row.get("note") or label),
                )
                return ""
            return str(row.get("note") or f"{label} belum tersimpan")
        except EngineError as exc:
            return f"{label} {exc.spec.code}: {exc.detail or exc.spec.message_id}"
        except Exception as exc:  # noqa: BLE001 - satu model gagal, model berikut tetap dicoba
            return f"{label} {exc}"

    def _publish_transform(
        self, file_id: str, running: bool, current: str | None, note: str
    ) -> None:
        with self._transform_lock:
            if self._transform.get("file_id") != file_id:
                return
            self._transform["running"] = running
            self._transform["current"] = current
            self._transform["note"] = note

    def _finish_transform(self, file_id: str, note: str) -> None:
        self._publish_transform(file_id, False, None, note)

    def mark(self, frame_id: str) -> tuple[str, str]:
        with self._lock:
            self._reject_lost(frame_id)
            frame = self.pipeline.ring.get(frame_id)
        if frame is None:
            raise EngineError("VID-002", frame_id)
        video = self._settings.thresholds.video
        path, digest = store_jpeg(
            self._marks, frame, video.display_max_side, video.display_jpeg_quality
        )
        return str(path), digest

    def current_frame_jpeg(self) -> tuple[bytes, int, int] | None:
        """JPEG bingkai live ukuran penuh. None bila sumber belum punya gambar."""
        with self._lock:
            if self.pipeline.state != "live":
                return None
            frame = self.pipeline.ring.latest()
            if frame is None:
                return None
            bgr, width, height = frame.bgr, frame.width, frame.height
            quality = self._settings.thresholds.video.display_jpeg_quality
        from .video.encode import encode_jpeg

        return encode_jpeg(bgr, width, height, max(width, height), quality), width, height

    def video_view(self) -> dict[str, object]:
        with self._lock:
            shown = self.pipeline.last_display
            frame = self.pipeline.ring.latest()
            state = self.pipeline.state
            count = len(self.pipeline.ring)
            fps = self.pipeline.fps("display", time.monotonic())
            serial = self._serial
            warning = self.watchdog.warning
            detail = self.watchdog.detail
        level = turbidity_level(frame, self._settings.video.turbidity) if frame else None
        gpu = probe_gpu()
        return {
            "state": state,
            "frame_id": None if shown is None else shown.frame_id,
            "frame_count": count,
            "enhanced": bool(shown and shown.enhanced),
            "fps": fps,
            "recording": self._settings.video.recording.enabled,
            "turbidity_level": level,
            "turbidity_configured": configured(self._settings.video.turbidity),
            "gpu_util_pct": gpu.utilization_pct,
            "vram_used_mb": gpu.vram_used_mb,
            "vram_total_mb": gpu.vram_total_mb,
            "vram_budget_mb": self._settings.thresholds.performance.vram_budget_mb,
            "gpu_max_pct": self._settings.thresholds.performance.gpu_max_pct,
            "gpu_device": self.models.device_note,
            "lost": state == "lost",
            "snapshot_count": serial,
            "performance_warning": warning,
            "performance_detail": detail,
        }

    def performance_view(self) -> dict[str, object]:
        info = probe_gpu()
        with self._lock:
            fps = self.pipeline.fps("display", time.monotonic())
        return {
            "warning": self.watchdog.warning,
            "detail": self.watchdog.detail,
            "fps": fps,
            "gpu_util_pct": info.utilization_pct,
            "vram_used_mb": info.vram_used_mb,
            "vram_total_mb": info.vram_total_mb,
        }

    def vision_view(self) -> dict[str, object]:
        from .gpu.report import assemble_vision

        with self._lock:
            event = dict(self._vision)
            raw_kind = event.get("kind")
            kind = raw_kind if isinstance(raw_kind, str) else None
            if not publish_allowed(self.models.active, kind, self.models.state):
                event = {}
            preset = self.models.preset_name
            frame = self.pipeline.ring.latest()
        hydro = self._settings.hydrodetect
        spatial = self._settings.spatialsight
        view = assemble_vision(event, preset, hydro, spatial)
        view["frame_width"] = None if frame is None else frame.width
        view["frame_height"] = None if frame is None else frame.height
        tune = self.models.hydro_tune()
        view["confidence"] = tune["confidence"]
        view["imgsz"] = tune["imgsz"]
        view["process_res"] = self.models.spatial_tune()["process_res"]
        return view

    def set_hydro_tune(self, confidence: float, imgsz: int) -> dict[str, float | int]:
        return self.models.set_hydro_tune(confidence, imgsz)

    def set_spatial_tune(self, process_res: int) -> dict[str, int]:
        return self.models.set_spatial_tune(process_res)

    def canvas_assist(self, frame_id: str, view: str) -> dict[str, object]:
        """Berkas bantuan bila ada. Jika belum, model yang sedang dimuat."""
        from .measure.canvas_assist import assist_frame, read_assist
        from .video.decode import decode_png

        if view != "optical":
            cached = read_assist(self._assist, frame_id, view)
            if cached is not None:
                return cached
        path = self._evidence / f"{frame_id}.png"
        if not path.is_file():
            raise EngineError("VID-002", frame_id)
        width, height, raw = decode_png(path.read_bytes())
        if view == "optical":
            return assist_frame(self.models, self._settings, frame_id, raw, width, height, view)
        with self._assist_lock:
            return assist_frame(self.models, self._settings, frame_id, raw, width, height, view)

    def begin_prepare(self, frame_id: str, preset: str | None) -> dict[str, object]:
        """Mulai hitung tiga tampilan bergantian. Panggilan ulang menunggu yang jalan."""
        from .measure.canvas_assist import assist_job

        if not (self._evidence / f"{frame_id}.png").is_file():
            raise EngineError("VID-002", frame_id)
        with self._bake_lock:
            current = self._bake
            if current.get("frame_id") == frame_id and current.get("running"):
                return dict(current)
            self._bake_token += 1
            token = self._bake_token
            self._bake = assist_job(frame_id, True, "aquaclear", "", [])
            started = dict(self._bake)
        worker = threading.Thread(
            target=self._prepare_worker,
            args=(frame_id, preset, token),
            name="di-assist",
            daemon=True,
        )
        worker.start()
        return started

    def prepare_status(self, frame_id: str) -> dict[str, object]:
        from .measure.canvas_assist import assist_job

        with self._bake_lock:
            current = dict(self._bake)
        if current.get("frame_id") != frame_id:
            return assist_job(frame_id, False, None, "", [])
        return current

    def _prepare_worker(self, frame_id: str, preset: str | None, token: int) -> None:
        from .measure.canvas_assist import bake_views
        from .video.decode import decode_png

        rows: list[dict[str, object]] = []
        note = ""
        try:
            with self._assist_lock:
                if not self._token_is(token):
                    return
                path = self._evidence / f"{frame_id}.png"
                width, height, raw = decode_png(path.read_bytes())
                chosen = self._aqua_preset(frame_id, preset)
                rows = bake_views(
                    self.models,
                    self._settings,
                    frame_id,
                    raw,
                    width,
                    height,
                    self._assist,
                    chosen,
                    lambda view, done: self._publish(token, frame_id, True, view, "", done),
                    lambda: self._token_is(token),
                )
        except EngineError as exc:
            note = f"{exc.spec.code}: {exc.detail or exc.spec.message_id}"
        except Exception as exc:  # noqa: BLE001 - utas bantuan harus selesai meski model gagal
            note = str(exc)
        if self._token_is(token):
            self._publish(token, frame_id, False, None, note, rows)

    def _publish(
        self,
        token: int,
        frame_id: str,
        running: bool,
        current: str | None,
        note: str,
        views: list[dict[str, object]],
    ) -> None:
        from .measure.canvas_assist import assist_job

        with self._bake_lock:
            if token != self._bake_token:
                return
            self._bake = assist_job(frame_id, running, current, note, list(views))

    def _token_is(self, token: int) -> bool:
        with self._bake_lock:
            return token == self._bake_token

    def _aqua_preset(self, frame_id: str, requested: str | None) -> str | None:
        chosen = requested or self._recorded_preset(frame_id)
        if isinstance(chosen, str) and chosen in self._settings.aquaclear.presets:
            return chosen
        return None

    def _recorded_preset(self, frame_id: str) -> str | None:
        path = self._evidence / f"{frame_id}.json"
        if not path.is_file():
            return None
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        preset = loaded.get("aquaclear_preset") if isinstance(loaded, dict) else None
        return preset if isinstance(preset, str) else None

    def estimate_spatial(self, frame_id: str, spec: dict[str, object]) -> dict[str, object]:
        """Satu forward pass untuk seluruh garis pada PNG beku, lalu lepas SpatialSight.

        Model tidak dibiarkan aktif. Frame video berikut tidak masuk GPU sampai tombol
        ukur ditekan lagi.
        """
        path = self._evidence / f"{frame_id}.png"
        if not path.is_file():
            raise EngineError("VID-002", frame_id)
        from .video.decode import decode_png

        width, height, raw = decode_png(path.read_bytes())
        self._live_infer.cancel()
        finished = False
        with self._assist_lock:
            try:
                self._ensure_spatial()
                event = self.models.geometry(raw, width, height, frame_id, spec)
                finished = True
                return {key: value for key, value in event.items() if key != "event"}
            finally:
                self._release_spatial_after_cycle(spec, finished)

    def _ensure_spatial(self) -> None:
        if self.models.state == "ready" and self.models.active == "spatialsight":
            return
        self.models.switch("spatialsight")

    def _release_spatial_after_cycle(self, spec: dict[str, object], finished: bool) -> None:
        """Batalkan antrean live, lalu kosongkan VRAM SpatialSight."""
        self._live_infer.cancel()
        if self.models.active != "spatialsight":
            return
        with contextlib.suppress(EngineError):
            self.models.switch("optical")
        lengths = spec.get("lengths")
        count = len(lengths) if isinstance(lengths, list) else 0
        if finished:
            note = f"SpatialSight satu siklus selesai, {count} garis. Prediksi dihentikan."
        else:
            note = "SpatialSight prediksi dihentikan."
        sys.stderr.write(note + "\n")
        sys.stderr.flush()

    def compare_view(self) -> dict[str, object]:
        from .video.compare import compare_payload

        video = self._settings.thresholds.video
        with self._lock:
            frame = self.pipeline.ring.latest()
            shown = self.pipeline.last_display
        jpeg = None if shown is None else shown.jpeg
        raw_jpeg = None if shown is None else shown.raw_jpeg
        return compare_payload(
            frame, jpeg, video.display_max_side, video.display_jpeg_quality, raw_jpeg
        )

    def compare_packet(self) -> tuple[dict[str, object], list[bytes]]:
        with self._lock:
            shown = self.pipeline.last_display
            state = self.pipeline.state
        frame_id = None if shown is None else shown.frame_id
        parts: list[bytes] = []
        if shown is not None and state != "lost":
            if shown.raw_jpeg is not None:
                parts.append(shown.raw_jpeg)
            if shown.jpeg:
                parts.append(shown.jpeg)
        return {"state": state, "frame_id": frame_id, "parts": len(parts)}, parts

    def display_packet(self) -> tuple[dict[str, object], bytes | None]:
        with self._lock:
            shown = self.pipeline.last_display
            state = self.pipeline.state
        jpeg = None if shown is None or state == "lost" else shown.jpeg
        return {
            "state": state,
            "frame_id": None if shown is None else shown.frame_id,
            "enhanced": bool(shown and shown.enhanced),
        }, jpeg

    def set_models_dir(self, config_dir: Path, configured: str) -> None:
        self.models.set_models_dir(resolve_models_dir(config_dir, configured))

    def close_session(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None
        self._capture.stop()
        self.models.close()
        self.cache.clear()

    def _push_many(self, frames: list[StoredFrame]) -> list[str]:
        ids: list[str] = []
        with self._lock:
            for frame in frames:
                self.pipeline.push(frame)
                self._cache_display(frame)
                ids.append(frame.frame_id)
        return ids

    def _ingest(self, width: int, height: int, raw: bytes) -> None:
        frame = StoredFrame(uuid7(), time.monotonic(), width, height, raw)
        with self._lock:
            self.pipeline.push(frame)
            self._cache_display(frame)

    def _reject_lost(self, frame_id: str) -> None:
        if self.pipeline.state == "lost":
            raise EngineError("VID-001", frame_id)

    def _open_configured_source(self) -> None:
        source = self._settings.video.source
        if source.kind is None:
            return
        try:
            self.open_device(source.kind, source.path, source.device_index, source.rtsp_url)
        except EngineError as exc:
            self._on_error(exc.spec.code, exc.detail)

    def _cache_display(self, frame: StoredFrame) -> None:
        shown = self.pipeline.last_display
        if shown is not None and shown.frame_id == frame.frame_id:
            self.cache.put(f"display/{frame.frame_id}", shown.jpeg)

    def _enhance(self, frame: StoredFrame) -> tuple[bytes, int, int] | None:
        if self._defer_gpu():
            self._live_infer.submit(frame)
            return None
        if not self._assist_lock.acquire(blocking=False):
            return None
        try:
            return self._enhance_locked(frame, None)
        finally:
            self._assist_lock.release()

    def _defer_gpu(self) -> bool:
        """HydroDetect dan SpatialSight tidak menahan gambar kamera."""
        return self.models.state == "ready" and self.models.active in {
            "hydrodetect",
            "spatialsight",
        }

    def _infer_later(self, frame: StoredFrame, generation: int) -> None:
        if not self._assist_lock.acquire(blocking=False):
            return
        try:
            self._enhance_locked(frame, generation)
        finally:
            self._assist_lock.release()

    def _enhance_locked(
        self, frame: StoredFrame, generation: int | None
    ) -> tuple[bytes, int, int] | None:
        kind = self.models.active
        try:
            raw = self.models.infer(frame)
        except EngineError as exc:
            self._on_error(exc.spec.code, exc.detail)
            return None
        event = self.models.last_result
        with self._lock:
            if generation is not None and not self._live_infer.accepts(generation):
                return None
            if not publish_allowed(self.models.active, kind, self.models.state):
                return None
            self._vision = {} if event is None else dict(event)
        if raw is None:
            return None
        width = int((event or {}).get("out_width") or frame.width)
        height = int((event or {}).get("out_height") or frame.height)
        if width * height * 3 != len(raw):
            width, height = frame.width, frame.height
        return raw, width, height

    def _display_fps(self) -> float | None:
        with self._lock:
            return self.pipeline.fps("display", time.monotonic())

    def _check_geometry(self, count: int, width: int, height: int) -> None:
        video = self._settings.thresholds.video
        limit = video.fps * int(video.ring_buffer_s)
        if not 1 <= count <= max(1, limit):
            raise EngineError("API-002", "jumlah frame di luar ring buffer")
        if width < 2 or height < 2 or width > video.width or height > video.height:
            raise EngineError("API-002", "ukuran frame di luar config video")

    def _loop(self) -> None:
        interval = self._settings.thresholds.performance.watchdog_interval_s
        while not self._stop.wait(interval):
            self.poll()


def resolve_models_dir(config_dir: Path, configured: str) -> Path:
    path = Path(configured)
    return path if path.is_absolute() else config_dir.parent / path


def build_runtime(
    settings: Settings,
    config_dir: Path,
    data_dir: Path,
    on_error: Callable[[str, str | None], None],
) -> Runtime:
    models_dir = resolve_models_dir(config_dir, settings.app.models.dir)
    return Runtime(settings, models_dir, data_dir, on_error, VramProbe())


def _noop_audit(action: str, entity: str, entity_id: str, detail: str) -> None:
    del action, entity, entity_id, detail


def _synthetic_frames(count: int, width: int, height: int, settings: Settings) -> list[StoredFrame]:
    now = time.monotonic()
    step = 1.0 / settings.thresholds.video.fps
    frames: list[StoredFrame] = []
    for index in range(count):
        frames.append(
            StoredFrame(
                uuid7(),
                now - (count - 1 - index) * step,
                width,
                height,
                gradient_bgr(width, height, index),
            )
        )
    return frames
