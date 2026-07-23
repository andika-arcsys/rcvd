# AGENTS.md

## Cursor Cloud specific instructions

### What this is
`rcvd-pycameraserver-modern` is a Python 3.12 / Flask 3 clone of PyCameraServer.
It is a **two-process** app; understand this before running it:

- `main.py` — the "mode selector" server (default port from `-o`, e.g. 8000). It
  serves the upload/URL form (`templates/main.html`). On each upload it launches
  `editor.py` **as a subprocess** and redirects the browser to it.
- `editor.py` — the per-source "editor" server that runs the OpenCV
  `ProcessingEngine` in a background thread and serves the live MJPEG stream
  (`/video`), stats (`/stats`), and controls (`templates/index.html`).

Standard run commands live in `README.md` (`python main.py -i 0.0.0.0 -o 8000`,
and the manual `python editor.py ...` invocation). The venv is at `.venv`.

### Non-obvious gotchas
- **Redirect uses `0.0.0.0`.** After an upload, `main.py` redirects to
  `http://0.0.0.0:<port>`. If a browser fails to open that, replace the host with
  `localhost` (same port).
- **Port auto-increments.** `main.py` bumps `connection_port` on every GET of
  `/`, so the spawned `editor.py` port is usually `8001`, `8002`, ... not the
  base port. Follow the redirect rather than hard-coding the editor port.
- **Models are optional.** Nothing is committed under `models/`. Every neural
  mode (YOLO, Mask R-CNN, Caffe colorizer, super-res, ESRGAN) falls back to a
  plain OpenCV effect and shows a "files missing; using fallback" status. The app
  runs fully without any model download — good enough for end-to-end testing.
- **`requirements-cu132.txt` and `requirements-optional-ai.txt` are optional and
  NOT needed to run/test the app.** The former pulls Torch from the CUDA 13.2
  index (a GPU wheel) and should be skipped on CPU-only cloud VMs;
  `requirements.txt` alone is sufficient.
- **`editor.py` prints `started`** to stdout once the processing thread is ready;
  `main.py` waits for that line before redirecting.

### Lint / test / build
- Lint: `ruff check .` (config in `pyproject.toml`). Note there are 2 pre-existing
  `F401` unused-import warnings in `ESRGAN/architecture.py` and `processing.py`;
  they are not introduced by setup.
- Tests: there is **no automated test suite** in this repo.
- Build: none — it is a plain Flask app run directly with `python`.
