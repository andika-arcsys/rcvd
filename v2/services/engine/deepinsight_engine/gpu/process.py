"""Pegang proses pekerja dan salinan frame lewat shared memory."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping
from multiprocessing.shared_memory import SharedMemory
from queue import Empty, Queue
from threading import Thread
from typing import Any

from ..core.errors import REGISTRY, EngineError
from ..video.frames import StoredFrame


class WorkerHandle:
    def __init__(self, timeout_s: float, env: Mapping[str, str] | None = None) -> None:
        self._timeout = timeout_s
        self._env = dict(env or {})
        self._queue: Queue[str] = Queue()
        self._proc: subprocess.Popen[str] | None = None
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

    def infer(self, frame: StoredFrame) -> bytes | None:
        shared = SharedMemory(create=True, size=len(frame.bgr))
        try:
            view: Any = shared.buf
            view[: len(frame.bgr)] = frame.bgr
            self.request(_infer_payload(frame, shared.name))
            event = self.read_event()
            self.last_event = event
            _raise_if_error(event)
            if not event.get("enhanced"):
                return None
            return bytes(view[: len(frame.bgr)])
        finally:
            shared.close()
            shared.unlink()

    def unload(self, timeout: float) -> bool:
        self.request({"cmd": "unload"})
        try:
            event = self.read_event(timeout)
        except EngineError:
            return False
        return event.get("event") == "unloaded"

    def kill(self) -> None:
        proc = self._proc
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
