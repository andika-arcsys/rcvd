"""Pilih backend SpatialSight.

Bawaan konsol adalah Depth Anything 3 dan tidak membutuhkan berkas lokal.
Depth Pro dan ONNX hanya dipakai bila backend-nya ``depth_pro``.
"""

from __future__ import annotations

from pathlib import Path


def spatial_choice(
    backend: str, root: Path, onnx: str | None, checkpoint: str | None
) -> tuple[str, Path | None] | None:
    if backend == "depth_anything3":
        return ("depth_anything3", None)
    return spatial_source(root, onnx, checkpoint)


def spatial_source(root: Path, onnx: str | None, checkpoint: str | None) -> tuple[str, Path] | None:
    if checkpoint:
        weights = root / checkpoint
        if weights.is_file():
            return ("depth_pro", weights)
    if onnx:
        model = root / onnx
        if model.is_file():
            return ("onnx", model)
    return None


def missing_spatial_detail(onnx: str | None, checkpoint: str | None) -> str:
    left = checkpoint or "spatialsight/depth_pro.pt"
    right = onnx or "spatialsight/model.onnx"
    return f"{left} atau {right}"
