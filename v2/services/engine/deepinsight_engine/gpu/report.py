"""Menyusun jawaban /vision. Filter kelas hanya menandai, tidak membuang kandidat."""

from __future__ import annotations

from ..core.config import HydrodetectConfig, SpatialSightConfig
from .vision import apply_class_filter


def assemble_vision(
    event: dict[str, object],
    preset: str | None,
    hydro: HydrodetectConfig,
    spatial: SpatialSightConfig,
) -> dict[str, object]:
    kind = event.get("kind")
    depth = _depth(event.get("depth"), spatial.relative_label) if kind == "spatialsight" else None
    return {
        "frame_id": _text(event.get("frame_id")),
        "kind": kind if isinstance(kind, str) else None,
        "preset": preset,
        "candidates": _candidates(event, hydro),
        "depth": depth,
        "classes": _classes(hydro),
    }


def _candidates(event: dict[str, object], hydro: HydrodetectConfig) -> list[dict[str, object]]:
    raw = event.get("candidates")
    if event.get("kind") != "hydrodetect" or not isinstance(raw, list):
        return []
    rows = [item for item in raw if isinstance(item, dict)]
    return apply_class_filter(rows, hydro.hidden_by_default)


def _depth(raw: object, label: str) -> dict[str, object] | None:
    if not isinstance(raw, dict) or raw.get("label") != label:
        return None
    values = raw.get("values")
    width, height = raw.get("width"), raw.get("height")
    if not isinstance(width, int) or not isinstance(height, int):
        return None
    if not isinstance(values, list) or any(not isinstance(item, int | float) for item in values):
        return None
    if any(not 0 <= float(item) <= 1 for item in values):
        return None
    scaled = [float(item) for item in values]
    row: dict[str, object] = {"width": width, "height": height, "values": scaled, "label": label}
    jpeg = raw.get("jpeg_b64")
    if isinstance(jpeg, str) and jpeg:
        row["jpeg_b64"] = jpeg
    return row


def _classes(hydro: HydrodetectConfig) -> list[dict[str, object]]:
    hidden = set(hydro.hidden_by_default)
    return [
        {"name": name, "hidden_by_default": name in hidden, "color": hydro.colors[name]}
        for name in hydro.filter_names
    ]


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None
