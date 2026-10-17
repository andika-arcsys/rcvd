"""Pemuatan dan validasi config YAML. Semua ambang berasal dari sini."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from .errors import EngineError

Access = Literal["full", "view", "none"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PipeValues(_Strict):
    inch_16: float
    inch_8: float


class Calibration(_Strict):
    rel_uncertainty_basis: Literal["2sigma", "1sigma"]
    click_sigma_px: float
    valid_max_rel: float
    estimate_max_rel: float
    diameter_sanity_pct: float
    edge_risk_px: float
    camera_file_required_for_valid: bool

    @model_validator(mode="after")
    def _ordered(self) -> Calibration:
        if not 0 < self.valid_max_rel < self.estimate_max_rel < 1:
            raise ValueError("Harus 0 < valid_max_rel < estimate_max_rel < 1")
        return self


class RodTest(_Strict):
    length_m: float
    tolerance_pct: float


class Freeze(_Strict):
    max_delta_cm: float


class Span(_Strict):
    rope_tolerance_pct: float
    segment_target_m: float
    warning_ratio: float
    critical_limit_m: PipeValues
    resurvey_months: int


class Measure(_Strict):
    heron_rel_tol: float
    boundary_tol: float
    undistort_iterations: int


class Pipe(_Strict):
    nominal_od_mm: PipeValues


class IntervalYears(_Strict):
    low: int
    low_to_moderate: int
    moderate_and_above: int


class Auth(_Strict):
    max_attempts: int
    lock_minutes: int


class Performance(_Strict):
    watchdog_interval_s: float
    fps_min: float
    fps_window_s: float
    vram_max_pct: float
    gpu_max_pct: float
    gpu_window_s: float
    vram_baseline_tolerance_mb: float
    unload_timeout_s: float
    load_timeout_s: float


class Video(_Strict):
    width: int
    height: int
    fps: int
    lost_signal_s: float
    ring_buffer_s: float
    display_max_side: int
    display_jpeg_quality: int
    fps_sample_s: float


class Cache(_Strict):
    max_mb: int


class Thresholds(_Strict):
    schema_version: int
    calibration: Calibration
    rod_test: RodTest
    freeze: Freeze
    span: Span
    measure: Measure
    pipe: Pipe
    inspection_interval_years: IntervalYears
    auth: Auth
    performance: Performance
    video: Video
    cache: Cache


class AppInfo(_Strict):
    name: str
    version: str
    env: Literal["dev", "prod"]
    language: str
    data_dir: str | None


class EngineNet(_Strict):
    host: str
    port: int
    cors_origins: list[str]


class LoggingCfg(_Strict):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"]
    rotate_mb: int
    backups: int


class Models(_Strict):
    dir: str
    active: str | None


class ModelEntry(_Strict):
    requires_gpu: bool
    onnx: str | None = None
    classes: str | None = None
    metadata: str | None = None


class ModelCatalog(_Strict):
    schema_version: int
    entries: dict[str, ModelEntry]


class AquaPreset(_Strict):
    clahe_clip: float
    clahe_tile: int
    dehaze: float

    @model_validator(mode="after")
    def _range(self) -> AquaPreset:
        if not 0 <= self.dehaze <= 1:
            raise ValueError("dehaze harus di antara 0 dan 1")
        if self.clahe_tile < 1:
            raise ValueError("clahe_tile minimal 1")
        return self


class AquaclearConfig(_Strict):
    schema_version: int
    default: str
    presets: dict[str, AquaPreset]

    @model_validator(mode="after")
    def _default_exists(self) -> AquaclearConfig:
        if self.default not in self.presets:
            raise ValueError("preset bawaan tidak ada di daftar")
        return self


class AppConfig(_Strict):
    schema_version: int
    app: AppInfo
    engine: EngineNet
    logging: LoggingCfg
    models: Models


class RolesConfig(_Strict):
    schema_version: int
    roles: list[str]
    default_admin_roles: list[str]
    menus: dict[str, dict[str, Access]]

    @model_validator(mode="after")
    def _complete_matrix(self) -> RolesConfig:
        for menu, row in self.menus.items():
            missing = set(self.roles) - set(row)
            extra = set(row) - set(self.roles)
            if missing or extra:
                raise ValueError(
                    f"Menu {menu}: peran kurang {sorted(missing)}, berlebih {sorted(extra)}"
                )
        return self


class ControlsConfig(_Strict):
    schema_version: int
    keyboard: dict[str, str]
    gamepad: dict[str, str]


class Settings(_Strict):
    """Seluruh config yang dimuat saat engine mulai."""

    app: AppConfig
    thresholds: Thresholds
    roles: RolesConfig
    controls: ControlsConfig
    models: ModelCatalog
    aquaclear: AquaclearConfig


def _load_yaml(path: Path) -> object:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise EngineError("SYS-001", f"{path.name}: {exc}") from exc


def _validate[T: BaseModel](model: type[T], path: Path) -> T:
    try:
        return model.model_validate(_load_yaml(path))
    except ValidationError as exc:
        raise EngineError("SYS-001", f"{path.name}: {exc}") from exc


def load_settings(config_dir: Path) -> Settings:
    return Settings(
        app=_validate(AppConfig, config_dir / "app.yaml"),
        thresholds=_validate(Thresholds, config_dir / "thresholds.yaml"),
        roles=_validate(RolesConfig, config_dir / "roles.yaml"),
        controls=_validate(ControlsConfig, config_dir / "controls.yaml"),
        models=_validate(ModelCatalog, config_dir / "models.yaml"),
        aquaclear=_validate(AquaclearConfig, config_dir / "aquaclear_presets.yaml"),
    )
