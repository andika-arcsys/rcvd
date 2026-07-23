"""Streaming processor for the modern PyCameraServer clone."""

from __future__ import annotations

import os
import threading
import time
from copy import deepcopy
from pathlib import Path

import cv2
import numpy as np

from model_adapters import ModelHub
from render_modes import render_with_mode
from settings import DEFAULT_SETTINGS, DEFAULT_STATES, RENDER_FOLDER, UPLOAD_FOLDER


states_dict = deepcopy(DEFAULT_STATES)
settings_ajax = deepcopy(DEFAULT_SETTINGS)
timer_start = 0.0
user_time = "0:0"
output_frame: np.ndarray | None = None
progress = 0.0
fps = 0.0
cap: cv2.VideoCapture | None = None
lock = threading.Lock()


class ProcessingEngine:
    def __init__(self, args: dict, upload_folder: str = UPLOAD_FOLDER) -> None:
        self.args = args
        self.port = int(args["port"])
        self.upload_folder = Path(upload_folder)
        self.render_folder = Path(RENDER_FOLDER)
        self.source = str(args["source"])
        self.mode = str(args["mode"])
        self.mode_code = str(args["optionsList"] or "a")
        self.model_hub = ModelHub(prefer_cuda=True)
        self.writer: cv2.VideoWriter | None = None
        self.started_rendering = False
        self.current_frame: np.ndarray | None = None
        self.background_capture = self._open_background()
        self.capture: cv2.VideoCapture | None = None
        self.last_position = 1
        self._configure_initial_state()

    def run(self) -> None:
        global output_frame, progress, fps, cap, user_time

        self.render_folder.mkdir(parents=True, exist_ok=True)
        self.upload_folder.mkdir(parents=True, exist_ok=True)
        self._open_source_capture()
        print("started", flush=True)

        while states_dict["working_on"]:
            start_moment = time.perf_counter()
            self._apply_browser_commands()
            frame = self._read_frame()
            background = self._read_background()
            if frame is None:
                frame = self._placeholder_frame("Waiting for a readable frame or uploaded source")

            states_dict["view_source"] = bool(settings_ajax.get("viewSource", False))
            rendered = frame.copy()
            if not states_dict["view_source"]:
                rendered = render_with_mode(
                    states_dict["render_mode"],
                    settings_ajax,
                    rendered,
                    background,
                    self.model_hub,
                    states_dict,
                    self.started_rendering,
                )

            self.current_frame = rendered
            self._handle_outputs(rendered)

            elapsed = max(time.perf_counter() - start_moment, 1e-6)
            fps = 1 / elapsed
            states_dict["frame_processed"] += 1
            progress = self._calculate_progress()

            preview = self._build_preview(rendered, fps, progress)
            with lock:
                output_frame = preview
                cap = self.capture
                user_time = f"{round(time.perf_counter())}:{round(timer_start)}"

            time.sleep(0.01)

        self.close()

    def set_uploaded_file(self, filename: str, source_mode: str) -> None:
        states_dict["source_mode"] = source_mode
        if source_mode == "image":
            states_dict["source_image"] = filename
        self.source = str(self.upload_folder / filename)
        self.mode = source_mode
        self._open_source_capture()

    def set_url(self, url: str, source_mode: str) -> None:
        states_dict["source_mode"] = source_mode
        states_dict["source_url"] = url
        self.source = url
        self.mode = source_mode
        self._open_source_capture()

    def close(self) -> None:
        if self.writer is not None:
            self.writer.release()
            self.writer = None
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        if self.background_capture is not None:
            self.background_capture.release()
            self.background_capture = None

    def _configure_initial_state(self) -> None:
        states_dict.update(deepcopy(DEFAULT_STATES))
        states_dict["source_mode"] = self.mode
        states_dict["source_url"] = self.source
        states_dict["render_mode"] = self.mode_code
        if self.mode == "image":
            states_dict["source_image"] = Path(self.source).name
        states_dict["output_file_page"] = self._output_file_name()
        states_dict["working_on"] = True

    def _open_source_capture(self) -> None:
        global cap
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        if self.mode in {"video", "ipcam", "youtube"}:
            source = self._resolve_youtube_url(self.source) if self.mode == "youtube" else self.source
            self.capture = cv2.VideoCapture(source)
            states_dict["total_frames"] = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT) or 1)
            if self.mode == "ipcam":
                states_dict["total_frames"] = 1
        elif self.mode == "image":
            states_dict["total_frames"] = 1
        cap = self.capture
        states_dict["frame_processed"] = 0
        states_dict["output_file_page"] = self._output_file_name()

    def _open_background(self) -> cv2.VideoCapture | None:
        path = Path("input_videos/space.webm")
        if path.exists():
            capture = cv2.VideoCapture(str(path))
            if capture.isOpened():
                return capture
        return None

    def _read_frame(self) -> np.ndarray | None:
        if self.mode == "image":
            image_path = Path(self.source)
            if not image_path.exists() and states_dict["source_image"]:
                image_path = self.upload_folder / states_dict["source_image"]
            return cv2.imread(str(image_path)) if image_path.exists() else None

        if self.capture is None or not self.capture.isOpened():
            return None

        if not self.started_rendering and self.mode in {"video", "youtube"}:
            position = max(1, int(settings_ajax.get("positionSliderValue", 1)))
            if position != self.last_position:
                self.capture.set(cv2.CAP_PROP_POS_FRAMES, position)
                self.last_position = position

        ok, frame = self.capture.read()
        if ok:
            return frame
        if self.mode in {"video", "youtube"}:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, 1)
        return None

    def _read_background(self) -> np.ndarray | None:
        if self.background_capture is None:
            return None
        ok, frame = self.background_capture.read()
        if ok:
            return frame
        self.background_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ok, frame = self.background_capture.read()
        return frame if ok else None

    def _apply_browser_commands(self) -> None:
        if settings_ajax.get("modeResetCommand"):
            states_dict["render_mode"] = str(settings_ajax.get("mode") or states_dict["render_mode"])
            states_dict["superres_model"] = str(settings_ajax.get("superresModel") or states_dict["superres_model"])
            states_dict["esrgan_model"] = str(settings_ajax.get("esrganModel") or states_dict["esrgan_model"])
        if settings_ajax.get("videoResetCommand"):
            self.started_rendering = True
            self._ensure_writer()
        if settings_ajax.get("videoStopCommand"):
            self.started_rendering = False
            if self.writer is not None:
                self.writer.release()
                self.writer = None
        if settings_ajax.get("screenshotCommand") and self.current_frame is not None:
            self._write_screenshot(self.current_frame)

    def _handle_outputs(self, rendered: np.ndarray) -> None:
        if self.mode == "image":
            output_path = self.render_folder / f"output{self.port}{Path(states_dict['source_image']).name}"
            cv2.imwrite(str(output_path), rendered)
        if self.started_rendering:
            self._ensure_writer(rendered)
            if self.writer is not None:
                self.writer.write(rendered)

    def _ensure_writer(self, frame: np.ndarray | None = None) -> None:
        if self.writer is not None or frame is None:
            return
        output_path = self.render_folder / f"output{self.port}{self._output_file_name()}"
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        height, width = frame.shape[:2]
        fps_out = 60 if states_dict["render_mode"] == "z" else 25
        self.writer = cv2.VideoWriter(str(output_path), fourcc, fps_out, (width, height), True)

    def _write_screenshot(self, frame: np.ndarray) -> None:
        path = self.render_folder / f"output{self.port}Screenshot.png"
        cv2.imwrite(str(path), frame)
        states_dict["screenshot_path"] = str(path)
        states_dict["screenshot_ready"] = True

    def _build_preview(self, frame: np.ndarray, current_fps: float, current_progress: float) -> np.ndarray:
        height, width = frame.shape[:2]
        preview_height = 460
        preview_width = max(1, round((preview_height / height) * width))
        preview = cv2.resize(frame, (preview_width, preview_height))
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(
            preview,
            f"FPS: {current_fps:.2f} ({width}x{height})",
            (40, 35),
            font,
            0.8,
            (0, 0, 255),
            2,
            lineType=cv2.LINE_AA,
        )
        if self.started_rendering:
            cv2.putText(
                preview,
                f"Writing to 'output{self.port}{self._output_file_name()}' ({current_progress:.2f}%)",
                (40, preview.shape[0] - 20),
                font,
                0.8,
                (255, 0, 255),
                2,
                lineType=cv2.LINE_AA,
            )
        return preview

    def _calculate_progress(self) -> float:
        if self.mode in {"video", "youtube"} and self.capture is not None:
            total = float(states_dict.get("total_frames") or 0)
            if total > 0:
                return min(100.0, (self.capture.get(cv2.CAP_PROP_POS_FRAMES) / total) * 100)
        return 0.0

    def _output_file_name(self) -> str:
        if self.mode == "youtube":
            return "youtube.avi"
        if self.mode == "ipcam":
            return "ipcam.avi"
        if self.mode == "image":
            image_name = Path(states_dict.get("source_image") or Path(self.source).name).name
            return image_name
        return f"{Path(self.source).name}.avi"

    def _resolve_youtube_url(self, url: str) -> str:
        try:
            import yt_dlp

            with yt_dlp.YoutubeDL({"quiet": True, "format": "best[ext=mp4]/best"}) as ydl:
                info = ydl.extract_info(url, download=False)
                return str(info["url"])
        except Exception:
            return url

    def _placeholder_frame(self, message: str) -> np.ndarray:
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        cv2.putText(frame, "PyCameraServer Modern Clone", (60, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 165, 255), 3)
        cv2.putText(frame, message, (60, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(frame, f"Mode: {states_dict['render_mode']}", (60, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        return frame


def process_frame(args: dict, app: object) -> None:
    _ = app
    ProcessingEngine(args).run()
