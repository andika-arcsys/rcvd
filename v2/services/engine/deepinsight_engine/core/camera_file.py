"""Skema berkas kamera. Templat berawalan garis bawah tidak menjadi kamera aktif."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, model_validator

from .errors import EngineError


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CameraFile(_Strict):
    schema_version: int
    id: str
    square_mm: float | None = None
    image_width: int | None = None
    image_height: int | None = None
    corners_cols: int | None = None
    corners_rows: int | None = None
    camera_matrix: list[float] | None = None
    dist_coeffs: list[float] | None = None
    rms: float | None = None
    calibrated_at: str | None = None

    @model_validator(mode="after")
    def _shape(self) -> CameraFile:
        if self.camera_matrix is not None and len(self.camera_matrix) != 9:
            raise ValueError("camera_matrix harus 9 angka")
        if self.dist_coeffs is not None and len(self.dist_coeffs) not in {4, 5, 8}:
            raise ValueError("dist_coeffs harus 4, 5, atau 8 angka")
        return self


def rms_decision(rms: float, good_px: float, max_px: float) -> str:
    """accept bila RMS <= good. warn sampai max. reject di atas max."""
    if rms <= good_px:
        return "accept"
    if rms <= max_px:
        return "warn"
    return "reject"


def camera_ids(folder: Path) -> list[str]:
    if not folder.is_dir():
        return []
    return sorted(path.stem for path in folder.glob("*.yaml") if not path.name.startswith("_"))


def validate_camera_files(folder: Path, validate: object) -> None:
    if not folder.is_dir():
        return
    checker = validate
    for path in sorted(folder.glob("*.yaml")):
        if not callable(checker):
            raise EngineError("SYS-002", "kamera")
        checker(CameraFile, path)
