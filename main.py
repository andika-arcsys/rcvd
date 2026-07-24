"""Mode selector server.

Usage:
    python main.py -i 0.0.0.0 -o 8000
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from flask import Flask, redirect, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

from resolv import resolv_bp
from settings import ALLOWED_EXTENSIONS, IMAGE_EXTENSIONS, UPLOAD_FOLDER, VIDEO_EXTENSIONS


app = Flask(__name__, static_url_path="/static")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.register_blueprint(resolv_bp)

connection_port = 8000
ip = "0.0.0.0"


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def start_process(auto_start: bool, port: int, source_type: str, source: str, mode: str, delay: int = 5) -> None:
    arg_list = [
        sys.executable,
        "-u",
        "editor.py",
        "-i",
        ip,
        "-o",
        str(port),
        "-s",
        str(source),
        "-c",
        mode,
        "-m",
        source_type,
    ]
    if auto_start:
        process = subprocess.Popen(arg_list, bufsize=0, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        started = False
        deadline = time.time() + 30
        while process.poll() is None and not started and time.time() < deadline:
            assert process.stdout is not None
            output = process.stdout.readline()
            if not output:
                continue
            text = output.decode("utf-8", errors="replace")
            print(text, end="")
            started = text.strip() == "started"
        time.sleep(1)
    else:
        subprocess.Popen(arg_list, bufsize=0)
        time.sleep(delay)


@app.route("/", methods=["GET", "POST"])
def upload_file():
    global connection_port

    if request.method == "POST":
        file = request.files.get("file")
        url = request.form.get("urlInput", "")
        mode = "".join(request.form.getlist("check")) or "a"

        if "youtu" in url:
            return start_analysis(connection_port, url, mode, "youtube")
        if "mjpg" in url or url.startswith(("rtsp://", "http://", "https://")):
            return start_analysis(connection_port, url, mode, "ipcam")

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            extension = filename.rsplit(".", 1)[1].lower()
            source_type = "image" if extension in IMAGE_EXTENSIONS else "video" if extension in VIDEO_EXTENSIONS else ""
            if source_type:
                return start_analysis(connection_port, str(Path(UPLOAD_FOLDER) / filename), mode, source_type)

    connection_port += 1
    return render_template("main.html")


@app.route("/uploads/<filename>")
def uploaded_file(filename: str):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


def start_analysis(port_to_render: int, file_to_render: str, mode: str, source_type: str):
    start_process(True, port_to_render, source_type, file_to_render, mode)
    return redirect(f"http://{ip}:{port_to_render}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--ip", type=str, required=True, help="ip address of the device")
    parser.add_argument("-o", "--port", type=int, required=True, help="port number of the server")
    args = vars(parser.parse_args())

    connection_port = args["port"]
    ip = str(args["ip"])
    Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
    app.run(host=args["ip"], port=args["port"], debug=False, threaded=True, use_reloader=False)
