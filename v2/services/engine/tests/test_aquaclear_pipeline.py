"""Pipeline AquaClear v2 sama dengan enhancer konsol RCVD pada satu frame."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from deepinsight_engine.core.config import load_settings
from deepinsight_engine.enhance.pipeline import UnderwaterEnhancer
from deepinsight_engine.gpu.aquaclear import apply_preset

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


def test_default_is_the_live_page_preset() -> None:
    settings = load_settings(CONFIG)
    assert settings.aquaclear.default == "light"
    raw = np.full((32, 24, 3), 80, dtype=np.uint8).tobytes()
    out = apply_preset(raw, 32, 24, settings.aquaclear.presets["light"])
    assert out != raw
    assert len(out) == len(raw)
