"""Pipeline AquaClear v2 sama dengan enhancer konsol RCVD pada satu frame."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from deepinsight_engine.core.config import load_settings
from deepinsight_engine.enhance.cuda_video import CUDA_PRESETS, open_cuda_enhancer
from deepinsight_engine.enhance.pipeline import UnderwaterEnhancer
from deepinsight_engine.gpu.aquaclear import apply_preset, open_enhancer

REPO = Path(__file__).resolve().parents[4]
CONFIG = Path(__file__).resolve().parents[3] / "config"


def test_each_button_matches_the_rcvd_preset() -> None:
    sys.path.insert(0, str(REPO))
    from underwater_enhance.pipeline import UnderwaterEnhancer as Source

    settings = load_settings(CONFIG)
    image = np.zeros((48, 64, 3), dtype=np.uint8)
    image[:, :, 1] = 140
    image[:, :20, 0] = 40
    image[:, 20:, 2] = 90
    expected = {"light": "realtime", "medium": "balanced", "heavy": "inspection"}
    for name, pipeline in expected.items():
        preset = settings.aquaclear.presets[name]
        assert preset.pipeline == pipeline
        left = Source.from_preset(pipeline).process(image)
        right = UnderwaterEnhancer.from_preset(pipeline).process(image.copy())
        assert left.shape == image.shape
        assert np.array_equal(left, right)


def test_cuda_realtime_uses_the_script_flags() -> None:
    chosen = CUDA_PRESETS["realtime"]
    assert (chosen.denoise, chosen.temporal_alpha, chosen.gamma, chosen.saturation) == (
        0.45,
        0.35,
        0.96,
        1.05,
    )
    for name in ("balanced", "inspection", "quality"):
        other = CUDA_PRESETS[name]
        assert other.gamma == 0.96
        assert other.saturation == 1.05


def test_open_enhancer_uses_cpu_when_cuda_is_absent() -> None:
    settings = load_settings(CONFIG)
    preset = settings.aquaclear.presets["light"]
    enhancer = open_enhancer(preset)
    if open_cuda_enhancer("realtime") is None:
        assert isinstance(enhancer, UnderwaterEnhancer)
        assert not getattr(enhancer, "uses_cuda", False)
    else:
        assert getattr(enhancer, "uses_cuda", False)


def test_default_is_the_live_page_preset() -> None:
    settings = load_settings(CONFIG)
    assert settings.aquaclear.default == "light"
    raw = np.full((32, 24, 3), 80, dtype=np.uint8).tobytes()
    out = apply_preset(raw, 32, 24, settings.aquaclear.presets["light"])
    assert out != raw
    assert len(out) == len(raw)
