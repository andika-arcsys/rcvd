import numpy as np
import pytest

from underwater_enhance import (
    PRESETS,
    PipelineConfig,
    UnderwaterEnhancer,
    color,
    dehaze,
    detail,
    metrics,
)
from underwater_enhance.cli import _parse_size
from underwater_enhance.temporal import MotionAdaptiveBlender, ParameterSmoother

RNG = np.random.default_rng(7)


def make_murky_frame(h=180, w=320):
    """Frame sintetis dengan green cast pekat + objek gelap."""
    frame = np.zeros((h, w, 3), dtype=np.float32)
    frame[..., 0] = 90   # B
    frame[..., 1] = 150  # G (dominan -> green cast)
    frame[..., 2] = 40   # R (teratenuasi)
    frame += RNG.normal(0, 5, frame.shape)
    frame[60:120, 100:220] = (55, 70, 45)  # objek "pipa" gelap
    return np.clip(frame, 0, 255).astype(np.uint8)


class TestColor:
    def test_red_compensation_raises_red_mean(self):
        img = make_murky_frame().astype(np.float32) / 255.0
        out = color.red_channel_compensation(img)
        assert out[..., 2].mean() > img[..., 2].mean()
        assert out.min() >= 0.0 and out.max() <= 1.0

    def test_shades_of_gray_neutralizes_cast(self):
        img = make_murky_frame().astype(np.float32) / 255.0
        gains = color.shades_of_gray_gains(img)
        balanced = color.apply_gains(img, gains)
        means = [balanced[..., c].mean() for c in range(3)]
        # Selisih antar kanal harus mengecil dibanding input green-cast.
        assert max(means) - min(means) < 0.15

    def test_stretch_expands_range(self):
        img = np.clip(RNG.uniform(0.4, 0.6, (50, 50, 3)), 0, 1).astype(np.float32)
        bounds = color.stretch_bounds(img)
        out = color.apply_stretch(img, bounds)
        assert out.max() - out.min() > img.max() - img.min()

    def test_clahe_output_shape_dtype(self):
        frame = make_murky_frame()
        out = color.clahe_lab(frame)
        assert out.shape == frame.shape and out.dtype == np.uint8


class TestDehaze:
    def test_guided_filter_smooths(self):
        noisy = RNG.uniform(0, 1, (64, 64)).astype(np.float32)
        guide = np.ones_like(noisy) * 0.5
        out = dehaze.guided_filter(guide, noisy, radius=8, eps=1e-3)
        assert out.std() < noisy.std()

    def test_udcp_increases_contrast(self):
        img = make_murky_frame().astype(np.float32) / 255.0
        out, atmo = dehaze.udcp_dehaze(img, analysis_scale=2)
        assert out.shape == img.shape
        assert atmo.shape == (3,)
        assert out.std() > img.std()  # haze removal menaikkan kontras

    def test_atmo_filter_callback_used(self):
        img = make_murky_frame().astype(np.float32) / 255.0
        fixed = np.array([0.5, 0.6, 0.2], dtype=np.float32)
        _, atmo = dehaze.udcp_dehaze(img, atmo_filter=lambda a: fixed)
        assert np.allclose(atmo, fixed)


class TestDetail:
    def test_unsharp_increases_sharpness(self):
        img = make_murky_frame().astype(np.float32) / 255.0
        out = detail.multiscale_unsharp_mask(img)
        lap_in = np.abs(np.diff(img[..., 1], axis=0)).mean()
        lap_out = np.abs(np.diff(out[..., 1], axis=0)).mean()
        assert lap_out > lap_in

    def test_unsharp_validates_args(self):
        img = np.zeros((10, 10, 3), np.float32)
        with pytest.raises(ValueError):
            detail.multiscale_unsharp_mask(img, sigmas=(1.0,), gains=(1.0, 2.0))

    def test_upscale_dimensions(self):
        frame = make_murky_frame(90, 160)
        out = detail.detail_preserving_upscale(frame, factor=2.0)
        assert out.shape == (180, 320, 3)


class TestTemporal:
    def test_parameter_smoother_ema(self):
        sm = ParameterSmoother(alpha=0.9)
        first = sm.smooth("k", np.array([1.0]))
        second = sm.smooth("k", np.array([2.0]))
        assert first[0] == 1.0
        assert np.isclose(second[0], 0.9 * 1.0 + 0.1 * 2.0)

    def test_blender_static_area_denoised(self):
        blender = MotionAdaptiveBlender(strength=0.5)
        base = make_murky_frame()
        noisy1 = np.clip(base + RNG.normal(0, 10, base.shape), 0, 255).astype(np.uint8)
        noisy2 = np.clip(base + RNG.normal(0, 10, base.shape), 0, 255).astype(np.uint8)
        blender.blend(noisy1)
        out = blender.blend(noisy2)
        err_blend = np.abs(out.astype(float) - base.astype(float)).mean()
        err_raw = np.abs(noisy2.astype(float) - base.astype(float)).mean()
        assert err_blend < err_raw  # noise berkurang di area statis


class TestPipeline:
    @pytest.mark.parametrize("preset", sorted(PRESETS))
    def test_presets_run_and_improve_quality(self, preset):
        enhancer = UnderwaterEnhancer.from_preset(preset)
        frame = make_murky_frame()
        out = None
        for _ in range(3):  # beberapa frame agar state temporal terisi
            out = enhancer.process(frame)
        assert out.shape == frame.shape and out.dtype == np.uint8
        m_raw = metrics.summarize(frame)
        m_enh = metrics.summarize(out)
        assert m_enh["uciqe"] > m_raw["uciqe"]
        assert m_enh["rms_contrast"] > m_raw["rms_contrast"]
        # Green cast harus ternetralkan: selisih mean antar kanal mengecil.
        spread_raw = np.ptp([frame[..., c].mean() for c in range(3)])
        spread_enh = np.ptp([out[..., c].mean() for c in range(3)])
        assert spread_enh < spread_raw

    def test_upscale_factor(self):
        enhancer = UnderwaterEnhancer(PipelineConfig(upscale_factor=2.0,
                                                     enable_dehaze=False))
        out = enhancer.process(make_murky_frame(90, 160))
        assert out.shape == (180, 320, 3)

    def test_unknown_preset_raises(self):
        with pytest.raises(KeyError):
            UnderwaterEnhancer.from_preset("does-not-exist")

    def test_reset_clears_state(self):
        enhancer = UnderwaterEnhancer.from_preset("quality")
        enhancer.process(make_murky_frame())
        enhancer.reset()
        assert enhancer._params._state == {}
        assert enhancer._blender._prev is None


class TestCli:
    @pytest.mark.parametrize("text,expected", [
        ("640x480", (640, 480)),
        ("1280X720", (1280, 720)),
    ])
    def test_parse_size_valid(self, text, expected):
        assert _parse_size(text) == expected

    @pytest.mark.parametrize("text", ["640", "0x480", "-640x480", "abcxdef", "640x480x3"])
    def test_parse_size_invalid(self, text):
        with pytest.raises(ValueError):
            _parse_size(text)
