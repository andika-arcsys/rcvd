"""Kontrak keluaran AI: poligon/RLE dan peta relatif. Bukan gambar mask, bukan meter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..core.config import HydrodetectConfig

RELATIVE_LABEL = "Preview relatif, bukan ukuran"


def rle_encode(mask: Sequence[Sequence[int]]) -> list[int]:
    """RLE baris-mayor. Hitungan pertama adalah deret nol bila piksel pertama hidup."""
    flat = [1 if cell else 0 for row in mask for cell in row]
    if not flat:
        return []
    counts = [0] if flat[0] == 1 else []
    previous = flat[0]
    run = 1
    for cell in flat[1:]:
        if cell == previous:
            run += 1
            continue
        counts.append(run)
        previous = cell
        run = 1
    counts.append(run)
    return counts


def passes_threshold(name: str, score: float, cfg: HydrodetectConfig) -> bool:
    limit = cfg.overrides.get(name, cfg.default_confidence)
    return score >= limit


def apply_class_filter(
    candidates: Sequence[Mapping[str, object]],
    hidden: Sequence[str],
) -> list[dict[str, object]]:
    """Menandai kelas yang disembunyikan. Tidak menghapus kandidat dari data."""
    hidden_set = set(hidden)
    marked: list[dict[str, object]] = []
    for item in candidates:
        name = str(item["class_name"])
        marked.append({**item, "hidden_by_filter": name in hidden_set})
    return marked


def hydro_event(frame_id: str, candidates: list[dict[str, object]]) -> dict[str, object]:
    return {
        "event": "result",
        "frame_id": frame_id,
        "enhanced": False,
        "kind": "hydrodetect",
        "candidates": candidates,
    }


def depth_event(frame_id: str, depth: dict[str, object]) -> dict[str, object]:
    if depth.get("label") != RELATIVE_LABEL:
        raise ValueError(RELATIVE_LABEL)
    return {
        "event": "result",
        "frame_id": frame_id,
        "enhanced": False,
        "kind": "spatialsight",
        "depth": depth,
    }


def trim_candidates(
    candidates: list[dict[str, object]],
    cfg: HydrodetectConfig,
) -> list[dict[str, object]]:
    kept = [
        item for item in candidates if passes_threshold(str(item["class_name"]), _score(item), cfg)
    ]
    kept.sort(key=_score, reverse=True)
    return kept[: cfg.max_candidates]


def _score(item: Mapping[str, object]) -> float:
    value = item["score"]
    if isinstance(value, int | float):
        return float(value)
    raise ValueError("skor kandidat")
