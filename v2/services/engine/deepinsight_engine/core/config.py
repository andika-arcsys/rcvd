"""Pemuatan dan validasi config YAML. Semua ambang berasal dari sini."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from .errors import EngineError
from .video_config import VideoFile

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
    canny_low: float
    canny_high: float
    camera_file_required_for_valid: bool
    min_baseline_px: int

    @model_validator(mode="after")
    def _ordered(self) -> Calibration:
        if not 0 < self.valid_max_rel < self.estimate_max_rel < 1:
            raise ValueError("Harus 0 < valid_max_rel < estimate_max_rel < 1")
        if not 0 <= self.canny_low < self.canny_high <= 255:
            raise ValueError("canny_low harus di bawah canny_high")
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


class Laser(_Strict):
    """Jarak dua titik laser. null sampai tim mengisi D-05. Hue mengikuti OpenCV 0–180."""

    ref_cm: float | None = None
    hue_low: int
    hue_high: int
    hue_wrap_low: int
    hue_wrap_high: int
    sat_min: int
    val_min: int
    min_area_px: int

    @model_validator(mode="after")
    def _ranges(self) -> Laser:
        hues = (self.hue_low, self.hue_high, self.hue_wrap_low, self.hue_wrap_high)
        if any(not 0 <= item <= 180 for item in hues):
            raise ValueError("hue laser harus 0–180")
        if self.hue_low > self.hue_high or self.hue_wrap_low > self.hue_wrap_high:
            raise ValueError("rentang hue laser terbalik")
        if any(not 0 <= item <= 255 for item in (self.sat_min, self.val_min)):
            raise ValueError("saturasi dan value harus 0–255")
        if self.min_area_px < 1:
            raise ValueError("min_area_px minimal 1")
        return self


class Interaction(_Strict):
    hit_px: int
    magnifier: int


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
    laser: Laser
    interaction: Interaction


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


class HydrodetectConfig(_Strict):
    schema_version: int
    default_confidence: float
    overrides: dict[str, float]
    hidden_by_default: list[str]
    filter_names: list[str]
    colors: dict[str, str]
    max_candidates: int

    @model_validator(mode="after")
    def _ranges(self) -> HydrodetectConfig:
        _unit_interval(self.default_confidence, "default_confidence")
        names = set(self.filter_names)
        for name, value in self.overrides.items():
            if name not in names:
                raise ValueError(f"override {name} tidak ada di filter")
            _unit_interval(value, name)
        for name in self.hidden_by_default:
            if name not in names:
                raise ValueError(f"kelas tersembunyi {name} tidak ada di filter")
        if set(self.colors) != names:
            raise ValueError("warna overlay harus satu per nama filter")
        if self.max_candidates < 1:
            raise ValueError("max_candidates minimal 1")
        return self


class SpatialSightConfig(_Strict):
    schema_version: int
    preview_max_side: int
    relative_label: str

    @model_validator(mode="after")
    def _label(self) -> SpatialSightConfig:
        if self.preview_max_side < 2:
            raise ValueError("preview_max_side minimal 2")
        if self.relative_label != "Preview relatif, bukan ukuran":
            raise ValueError("label SpatialSight harus tetap")
        return self


def _unit_interval(value: float, name: str) -> None:
    if not 0 < value <= 1:
        raise ValueError(f"{name} harus di antara 0 dan 1")


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


class Pipeline(_Strict):
    id: str
    name: str
    diameter: Literal["16", "8"]


class PipelineFile(_Strict):
    schema_version: int
    pipelines: list[Pipeline]


class UserAccount(_Strict):
    id: str
    name: str
    pin_hash: str
    roles: list[str]


class UsersFile(_Strict):
    schema_version: int
    users: list[UserAccount]


class Settings(_Strict):
    """Seluruh config yang dimuat saat engine mulai."""

    app: AppConfig
    thresholds: Thresholds
    roles: RolesConfig
    controls: ControlsConfig
    models: ModelCatalog
    aquaclear: AquaclearConfig
    hydrodetect: HydrodetectConfig
    spatialsight: SpatialSightConfig
    pipelines: PipelineFile
    users: UsersFile
    video: VideoFile


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
        hydrodetect=_validate(HydrodetectConfig, config_dir / "hydrodetect.yaml"),
        spatialsight=_validate(SpatialSightConfig, config_dir / "spatialsight.yaml"),
        pipelines=_validate(PipelineFile, config_dir / "pipelines.yaml"),
        users=_validate(UsersFile, config_dir / "users.yaml"),
        video=_validate(VideoFile, config_dir / "video.yaml"),
    )
