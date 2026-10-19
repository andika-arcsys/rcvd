"""Satu model aktif. Ganti model melepas pekerja lama, lalu mengukur VRAM."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from ..core.config import (
    AquaPreset,
    HydrodetectConfig,
    ModelCatalog,
    ModelEntry,
    SpatialSightConfig,
)
from ..core.errors import REGISTRY, EngineError
from ..video.frames import StoredFrame
from .probe import VramProbe
from .process import WorkerHandle


class ModelManager:
    def __init__(
        self,
        catalog: ModelCatalog,
        models_dir: Path,
        presets: dict[str, AquaPreset],
        default_preset: str,
        probe: VramProbe,
        unload_timeout_s: float,
        load_timeout_s: float,
        tolerance_mb: float,
        on_error: Callable[[str, str | None], None],
        worker_env: Mapping[str, str] | None = None,
        hydro: HydrodetectConfig | None = None,
        spatial: SpatialSightConfig | None = None,
        display_max_side: int = 0,
    ) -> None:
        self._catalog = catalog
        self._models_dir = models_dir
        self._presets = presets
        self._default_preset = default_preset
        self._probe = probe
        self._unload_timeout = unload_timeout_s
        self._load_timeout = load_timeout_s
        self._tolerance = tolerance_mb
        self._on_error = on_error
        self._worker_env = dict(worker_env or {})
        self._hydro = hydro
        self._spatial = spatial
        self._display_max_side = display_max_side
        self._hydro_tune: dict[str, float | int] = {
            "confidence": 0.5 if hydro is None else hydro.default_confidence,
            "imgsz": 640,
        }
        self._baseline = probe.snapshot()
        self._worker: WorkerHandle | None = None
        self.active: str | None = None
        self.preset_name: str | None = None
        self.last_result: dict[str, Any] | None = None
        self.state = "optical"
        self.killed_for_vram = False
        self.device_note: str | None = None

    def set_models_dir(self, models_dir: Path) -> None:
        self._models_dir = models_dir

    @property
    def gpu_available(self) -> bool:
        return self._baseline is not None

    @property
    def workers(self) -> int:
        return 1 if self._worker is not None and self._worker.alive() else 0

    @property
    def worker_pid(self) -> int | None:
        return None if self._worker is None else self._worker.pid

    def switch(self, name: str, preset: str | None = None) -> None:
        if name == "optical":
            self._to_optical()
            return
        entry = self._catalog.entries.get(name)
        if entry is None:
            raise EngineError("API-002", name)
        if entry.requires_gpu and not self.gpu_available:
            self._to_optical()
            raise EngineError("MDL-003", name)
        self._preset(preset)
        self.state = "unloading"
        self._release()
        self.state = "loading"
        self._worker = self._open(name, entry, preset)
        self.active = name
        self.preset_name = (preset or self._default_preset) if name == "aquaclear" else None
        self.last_result = None
        self.state = "ready"

    def hydro_tune(self) -> dict[str, float | int]:
        return dict(self._hydro_tune)

    def set_hydro_tune(self, confidence: float, imgsz: int) -> dict[str, float | int]:
        self._hydro_tune = {"confidence": confidence, "imgsz": imgsz}
        return self.hydro_tune()

    def geometry(
        self, raw: bytes, width: int, height: int, frame_id: str, spec: Mapping[str, Any]
    ) -> dict[str, Any]:
        worker = self._worker
        if self.state != "ready" or worker is None or self.active != "spatialsight":
            raise EngineError("MDL-002", "SpatialSight belum dimuat")
        return worker.geometry(raw, width, height, frame_id, spec)

    def infer(self, frame: StoredFrame) -> bytes | None:
        if self.state != "ready" or self._worker is None:
            return None
        extra = self._hydro_tune if self.active == "hydrodetect" else None
        raw = self._worker.infer(frame, extra)
        self.last_result = self._worker.last_event
        return raw

    def close(self) -> None:
        self._to_optical()

    def _to_optical(self) -> None:
        self.state = "unloading"
        self._release()
        self.active = None
        self.preset_name = None
        self.last_result = None
        self.device_note = None
        self.state = "optical"

    def _open(self, name: str, entry: ModelEntry, preset: str | None) -> WorkerHandle:
        worker = WorkerHandle(self._load_timeout, env=self._worker_env)
        worker.start()
        worker.request(self._load_payload(name, entry, preset))
        try:
            event = worker.read_event()
        except EngineError:
            worker.kill()
            self._fail_optical()
            raise
        if event.get("event") == "error":
            worker.kill()
            self._fail_optical()
            _raise_event(event)
        if event.get("event") != "ready":
            worker.kill()
            self._fail_optical()
            raise EngineError("MDL-002", str(event))
        note = event.get("device")
        self.device_note = None if note is None else str(note)
        return worker

    def _fail_optical(self) -> None:
        self._worker = None
        self.active = None
        self.preset_name = None
        self.last_result = None
        self.device_note = None
        self.state = "optical"

    def _release(self) -> None:
        worker = self._worker
        self._worker = None
        if worker is None:
            return
        exited = worker.unload(self._unload_timeout)
        if self._over_baseline() and not exited:
            worker.kill()
            self.killed_for_vram = True
            self._on_error("GPU-002", self.active)
            return
        if not exited:
            worker.kill()

    def _over_baseline(self) -> bool:
        reading = self._probe.snapshot()
        base = self._baseline
        if reading is None or base is None:
            return False
        return reading.used_mb - base.used_mb > self._tolerance

    def _load_payload(self, name: str, entry: ModelEntry, preset: str | None) -> dict[str, object]:
        chosen = self._preset(preset)
        return {
            "cmd": "load",
            "kind": name,
            "models_dir": str(self._models_dir),
            "onnx": entry.onnx,
            "weights": entry.weights,
            "checkpoint": entry.checkpoint,
            "classes": entry.classes,
            "preset": chosen.model_dump(),
            "hydro": None if self._hydro is None else self._hydro.model_dump(),
            "spatial": None if self._spatial is None else self._spatial.model_dump(),
            "display_max_side": self._display_max_side,
        }

    def _preset(self, name: str | None) -> AquaPreset:
        chosen = name or self._default_preset
        preset = self._presets.get(chosen)
        if preset is None:
            raise EngineError("API-002", chosen)
        return preset


def _raise_event(event: dict[str, object]) -> None:
    code = str(event.get("code") or "MDL-002")
    if code not in REGISTRY:
        code = "MDL-002"
    detail = event.get("detail")
    raise EngineError(code, None if detail is None else str(detail))
