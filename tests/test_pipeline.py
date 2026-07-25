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


class TestYoloIntegration:
    def test_invalid_mode_rejected(self):
        from underwater_enhance.yolo_integration import YoloUnderwaterInspector
        with pytest.raises(ValueError):
            YoloUnderwaterInspector("model.pt", mode="does-not-exist")

    def test_modes_exposed(self):
        from underwater_enhance.yolo_integration import MODES
        assert set(MODES) == {"raw", "hybrid", "enhanced", "compare", "quad"}

    def test_quad_view_grid_dimensions(self):
        from underwater_enhance.yolo_integration import _quad_view

        panels = [np.zeros((30, 40, 3), dtype=np.uint8) for _ in range(4)]
        out = _quad_view(*panels)
        assert out.shape == (60, 80, 3)

    def test_detection_label_includes_actual_stats(self):
        from underwater_enhance.yolo_integration import _detection_label
        assert _detection_label("RAW + YOLO", (3, 0.756)) == (
            "RAW + YOLO | 3 objek | conf avg: 0.76"
        )

    def test_mask_alpha_native_shape_and_smoothing(self):
        from underwater_enhance.yolo_integration import _mask_alpha

        mask = np.zeros((10, 10), dtype=np.float32)
        mask[2:8, 2:8] = 1.0
        alpha = _mask_alpha(mask, (20, 30), kernel_size=3)
        assert alpha.shape == (20, 30)
        assert alpha.min() >= 0.0 and alpha.max() <= 0.38
        assert 0.0 < alpha[10, 15] <= 0.38

    @pytest.mark.parametrize("name,official", [
        ("yolo26n-seg.pt", True),
        ("yolo11s.pt", True),
        ("yolov8m-pose.pt", True),
        ("best.pt", False),
        ("runs/segment/train/weights/best.pt", False),
    ])
    def test_official_weight_detection(self, name, official):
        from underwater_enhance.yolo_integration import _is_official_weight
        assert _is_official_weight(name) is official

    def test_resolve_device_override(self):
        import torch

        from underwater_enhance.yolo_integration import resolve_device
        device, half, _ = resolve_device("cpu")
        assert device == "cpu" and half is False
        if not torch.cuda.is_available():
            with pytest.raises(RuntimeError, match="tidak mendeteksi CUDA"):
                resolve_device("0")
            return
        device, half, _ = resolve_device("0")
        assert device == "0" and half is True

    def test_resolve_device_auto_no_gpu(self):
        import torch

        from underwater_enhance.yolo_integration import resolve_device
        if torch.cuda.is_available():
            pytest.skip("Mesin uji punya GPU; kasus fallback CPU tidak berlaku")
        device, half, desc = resolve_device()
        assert device == "cpu" and half is False
        assert "CUDA tidak terdeteksi" in desc

    def test_conf_default_displayed(self):
        from underwater_enhance.yolo_integration import build_parser
        args = build_parser().parse_args(["video.mp4", "--model", "m.pt"])
        assert args.conf == 0.7
        assert args.preset == "inspection"
        assert args.mask_smooth == 3

    @pytest.mark.parametrize("conf", [0.0, 0.7, 1.0])
    def test_confidence_validation_valid(self, conf):
        from underwater_enhance.yolo_integration import _validate_confidence
        assert _validate_confidence(conf) is None

    @pytest.mark.parametrize("conf", [-0.1, 1.1])
    def test_confidence_validation_invalid(self, conf):
        from underwater_enhance.yolo_integration import _validate_confidence
        assert "antara 0.0 dan 1.0" in _validate_confidence(conf)

    def test_validate_model_path_messages(self, tmp_path):
        from underwater_enhance.yolo_integration import _validate_model_path
        # Nama resmi -> valid meskipun belum ada di disk (auto-download).
        assert _validate_model_path("yolo26n-seg.pt") is None
        # File lokal yang ada -> valid.
        weight = tmp_path / "best.pt"
        weight.write_bytes(b"x")
        assert _validate_model_path(str(weight)) is None
        # File lokal yang tidak ada -> pesan error ramah.
        assert "tidak ditemukan" in _validate_model_path("best.pt")


class TestCudaBatchScript:
    def test_channel_quantiles_compatible_per_channel(self):
        import torch

        from scripts.enhance_video_cuda import _channel_quantiles

        # NCHW: setiap kanal punya distribusi berbeda.
        image = torch.tensor(
            [[[[0.0, 0.1], [0.2, 0.3]], [[0.4, 0.5], [0.6, 0.7]], [[0.8, 0.9], [1.0, 1.0]]]]
        )
        low, high = _channel_quantiles(image, 0.0, 1.0)
        assert torch.allclose(low, torch.tensor([0.0, 0.4, 0.8]))
        assert torch.allclose(high, torch.tensor([0.3, 0.7, 1.0]))


class TestCudaInspectionScript:
    def test_inspection_defaults_are_conservative(self):
        from scripts.enhance_video_inspection_cuda import build_parser

        args = build_parser().parse_args(["input.mp4", "output.mp4"])
        assert args.scale == 2.0
        assert args.illumination_strength == 0.35
        assert args.contrast_strength == 0.45
        assert args.temporal_alpha == 0.15

    def test_content_bounds_excludes_osd(self):
        from scripts.enhance_video_inspection_cuda import _content_bounds

        assert _content_bounds(720, 0.08, 0.07) == (58, 670)

    def test_aligned_temporal_blend_identical_frames_unchanged(self):
        from scripts.enhance_video_inspection_cuda import _temporal_blend_aligned

        frame = np.full((40, 60, 3), 123, dtype=np.uint8)
        gray = np.full((40, 60), 123, dtype=np.uint8)
        out = _temporal_blend_aligned(frame, frame, gray, gray, alpha=0.3)
        assert np.array_equal(out, frame)

    def test_osd_recompose_preserves_scaled_osd(self):
        from scripts.enhance_video_inspection_cuda import _recompose_osd

        original = np.zeros((10, 8, 3), dtype=np.uint8)
        original[:2] = (17, 23, 31)  # OSD top unik
        roi_up = np.full((12, 16, 3), 200, dtype=np.uint8)
        output = _recompose_osd(
            original, roi_up, top=2, bottom=8,
            output_size=(16, 20), output_top=4, output_bottom=16,
        )
        assert output.shape == (20, 16, 3)
        # Lanczos saat scale boleh menginterpolasi batas OSD, tetapi area interior
        # tetap berasal dari OSD asli dan tidak terkena enhancement ROI.
        assert np.all(output[:2] == (17, 23, 31))
        assert np.all(output[4:16] == 200)

    @pytest.mark.parametrize("scale,expected", [
        ("0.25", 0.25),
        ("0.5", 0.5),
        ("1", 1.0),
        ("2", 2.0),
        ("3", 3.0),
    ])
    def test_parser_accepts_downscale_and_upscale(self, scale, expected):
        from scripts.enhance_video_inspection_cuda import build_parser

        args = build_parser().parse_args(["input.mp4", "output.mp4", "--scale", scale])
        assert args.scale == expected


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
