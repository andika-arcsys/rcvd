"""Editor server compatible with the original PyCameraServer CLI."""

from __future__ import annotations

import argparse
import threading
import time
from pathlib import Path

import cv2
import psutil
from flask import Flask, Response, jsonify, render_template, request
from werkzeug.utils import secure_filename

import processing
from processing import ProcessingEngine
from settings import ALLOWED_EXTENSIONS, IMAGE_EXTENSIONS, RENDER_FOLDER, UPLOAD_FOLDER, VIDEO_EXTENSIONS


app = Flask(__name__, static_url_path="/static")
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

engine: ProcessingEngine | None = None
args: dict = {}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate():
    while processing.states_dict["working_on"]:
        with processing.lock:
            if processing.output_frame is None:
                frame = None
            else:
                frame = processing.output_frame.copy()
        if frame is None:
            time.sleep(0.03)
            continue
        flag, encoded_image = cv2.imencode(".jpg", frame)
        if not flag:
            continue
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + bytearray(encoded_image) + b"\r\n"


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        _handle_source_change()

    output_file = processing.states_dict.get("output_file_page", "render.avi")
    return render_template(
        "index.html",
        frame_processed=processing.states_dict["frame_processed"],
        pathToRenderedFile=f"{RENDER_FOLDER}/output{args['port']}{output_file}",
        pathToZipFile=f"{RENDER_FOLDER}/output{args['port']}.zip",
    )


@app.route("/video")
def video_feed():
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/stats", methods=["POST"])
def send_stats():
    frame_width_to_page = 0
    frame_height_to_page = 0
    screenshot_ready_local = False

    if processing.states_dict["screenshot_ready"]:
        screenshot_ready_local = True
        processing.states_dict["screenshot_ready"] = False

    if processing.cap is not None:
        frame_width_to_page = processing.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        frame_height_to_page = processing.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    return jsonify(
        {
            "value": processing.states_dict["frame_processed"],
            "totalFrames": processing.states_dict["total_frames"],
            "progress": round(processing.progress, 2),
            "fps": round(processing.fps, 2),
            "workingOn": processing.states_dict["working_on"],
            "cpuUsage": psutil.cpu_percent(),
            "freeRam": round((psutil.virtual_memory().available / 2.0**30), 2),
            "ramPercent": psutil.virtual_memory().percent,
            "frameWidth": frame_width_to_page,
            "frameHeight": frame_height_to_page,
            "currentMode": processing.states_dict["render_mode"],
            "userTime": processing.user_time,
            "screenshotReady": screenshot_ready_local,
            "screenshotPath": processing.states_dict["screenshot_path"],
        }
    )


@app.route("/settings", methods=["GET", "POST"])
def receive_settings():
    if request.method == "POST":
        processing.timer_start = time.perf_counter()
        payload = request.get_json(silent=True) or {}
        processing.settings_ajax.update(payload)
    return "", 200


def _handle_source_change() -> None:
    if engine is None:
        return
    textbox_string = request.form.get("textbox", "")
    if "youtu" in textbox_string:
        engine.set_url(textbox_string, "youtube")
        return
    if textbox_string.startswith(("rtsp://", "http://", "https://")) or "mjpg" in textbox_string:
        engine.set_url(textbox_string, "ipcam")
        return

    file = request.files.get("file")
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
        file.save(str(Path(app.config["UPLOAD_FOLDER"]) / filename))
        extension = filename.rsplit(".", 1)[1].lower()
        if extension in IMAGE_EXTENSIONS:
            engine.set_uploaded_file(filename, "image")
        elif extension in VIDEO_EXTENSIONS:
            engine.set_uploaded_file(filename, "video")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--ip", type=str, required=True, help="ip address of the device")
    parser.add_argument("-o", "--port", type=int, required=True, help="port number of the server")
    parser.add_argument("-s", "--source", type=str, required=True, help="file or URL to render")
    parser.add_argument("-c", "--optionsList", type=str, required=True, help="rendering mode code")
    parser.add_argument("-m", "--mode", type=str, required=True, help="source mode: ipcam, youtube, video or image")
    args = vars(parser.parse_args())

    Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
    Path(RENDER_FOLDER).mkdir(parents=True, exist_ok=True)
    engine = ProcessingEngine(args, app.config["UPLOAD_FOLDER"])
    thread = threading.Thread(target=engine.run, daemon=True)
    thread.start()
    app.run(host=args["ip"], port=args["port"], debug=False, threaded=True, use_reloader=False)
