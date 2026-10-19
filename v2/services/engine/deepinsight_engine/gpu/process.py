"""Pegang proses pekerja dan salinan frame lewat shared memory."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping
from multiprocessing.shared_memory import SharedMemory
from queue import Empty, Queue
from threading import Lock, Thread
from typing import Any

from ..core.errors import REGISTRY, EngineError
from ..video.frames import StoredFrame


class WorkerHandle:
    def __init__(self, timeout_s: float, env: Mapping[str, str] | None = None) -> None:
        self._timeout = timeout_s
        self._env = dict(env or {})
        self._queue: Queue[str] = Queue()
        self._proc: subprocess.Popen[str] | None = None
        self._io = Lock()
        self._shm: SharedMemory | None = None
        self._shm_size = 0
        self.last_event: dict[str, Any] | None = None

    @property
    def pid(self) -> int | None:
        return None if self._proc is None else self._proc.pid

    def alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self) -> None:
        env = os.environ.copy()
        env.update(self._env)
        self._proc = subprocess.Popen(
            [sys.executable, "-m", "deepinsight_engine.gpu.worker"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            env=env,
        )
        Thread(target=self._read_stdout, name="di-worker-stdout", daemon=True).start()

    def request(self, payload: dict[str, Any]) -> None:
        proc = self._require()
        if proc.stdin is None:
            raise EngineError("MDL-002", "stdin pekerja tertutup")
        try:
            proc.stdin.write(json.dumps(payload) + "\n")
            proc.stdin.flush()
        except OSError as exc:
            raise EngineError("MDL-002", "pekerja terputus") from exc

    def read_event(self, timeout: float | None = None) -> dict[str, Any]:
        try:
            line = self._queue.get(timeout=self._timeout if timeout is None else timeout)
        except Empty as exc:
            raise EngineError("MDL-002", "pekerja tidak menjawab") from exc
        loaded: dict[str, Any] = json.loads(line)
        return loaded

    def infer(self, frame: StoredFrame, extra: Mapping[str, Any] | None = None) -> bytes | None:
        with self._io:
            return self._infer_locked(frame, extra)

    def geometry(
        self, raw: bytes, width: int, height: int, frame_id: str, spec: Mapping[str, Any]
    ) -> dict[str, Any]:
        with self._io:
            return self._geometry_locked(raw, width, height, frame_id, spec)

    def _infer_locked(self, frame: StoredFrame, extra: Mapping[str, Any] | None) -> bytes | None:
        shared = self._buffer(len(frame.bgr))
        view: Any = shared.buf
        view[: len(frame.bgr)] = frame.bgr
        payload = _infer_payload(frame, shared.name)
        if extra:
            payload.update(extra)
        self.request(payload)
        event = self.read_event()
        self.last_event = event
        _raise_if_error(event)
        if not event.get("enhanced"):
            return None
        width = int(event.get("out_width") or frame.width)
        height = int(event.get("out_height") or frame.height)
        count = min(width * height * 3, len(view))
        return bytes(view[:count])

    def _geometry_locked(
        self, raw: bytes, width: int, height: int, frame_id: str, spec: Mapping[str, Any]
    ) -> dict[str, Any]:
        shared = self._buffer(len(raw))
        view: Any = shared.buf
        view[: len(raw)] = raw
        payload: dict[str, Any] = {
            "cmd": "geometry",
            "shm": shared.name,
            "width": width,
            "height": height,
            "frame_id": frame_id,
        }
        payload.update(spec)
        self.request(payload)
        event = self.read_event()
        _raise_if_error(event)
        return event

    def _buffer(self, size: int) -> SharedMemory:
        if self._shm is not None and self._shm_size >= size:
            return self._shm
        self._release_memory()
        self._shm = SharedMemory(create=True, size=size)
        self._shm_size = size
        return self._shm

    def _release_memory(self) -> None:
        shared = self._shm
        self._shm = None
        self._shm_size = 0
        if shared is None:
            return
        shared.close()
        try:
            shared.unlink()
        except FileNotFoundError:
            return

    def unload(self, timeout: float) -> bool:
        with self._io:
            try:
                self.request({"cmd": "unload"})
                try:
                    event = self.read_event(timeout)
                except EngineError:
                    return False
                return event.get("event") == "unloaded"
            finally:
                self._release_memory()

    def kill(self) -> None:
        proc = self._proc
        self._release_memory()
        if proc is None or proc.poll() is not None:
            return
        proc.kill()
        proc.wait(timeout=self._timeout)

    def _require(self) -> subprocess.Popen[str]:
        if self._proc is None:
            raise EngineError("MDL-002", "pekerja belum dimulai")
        return self._proc

    def _read_stdout(self) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        for line in proc.stdout:
            self._queue.put(line)


def _raise_if_error(event: dict[str, Any]) -> None:
    if event.get("event") != "error":
        return
    code = str(event.get("code") or "MDL-002")
    if code not in REGISTRY:
        code = "MDL-002"
    detail = event.get("detail")
    raise EngineError(code, None if detail is None else str(detail))


def _infer_payload(frame: StoredFrame, name: str) -> dict[str, Any]:
    return {
        "cmd": "infer",
        "shm": name,
        "width": frame.width,
        "height": frame.height,
        "frame_id": frame.frame_id,
    }
