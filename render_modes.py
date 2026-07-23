"""Mode dispatcher compatible with the original PyCameraServer controls."""

from __future__ import annotations

import cv2
import numpy as np

from mode_selector import (
    adjust_br_contrast,
    adjust_saturation,
    ascii_paint,
    blur_background_rcnn,
    cartoon_effect,
    color_canny_rcnn,
    color_objects_on_gray,
    denoise,
    draw_yolo_stats,
    extract_objects_yolo,
    objects_to_text_yolo,
    overlay_status,
    pencil_drawer,
    replace_background_rcnn,
    sharpening,
    sobel,
    two_colored,
)
from model_adapters import ModelHub
from settings import mode_code_to_name


def render_with_mode(
    mode_code: str,
    sliders_ajax: dict,
    main_frame: np.ndarray,
    frame_background: np.ndarray | None,
    model_hub: ModelHub,
    server_states: dict,
    started_rendering_video: bool,
) -> np.ndarray:
    rendering_mode = mode_code_to_name.get(mode_code, "extract_objects_yolo_mode")
    out = main_frame.copy()

    if rendering_mode in {
        "extract_objects_yolo_mode",
        "text_render_yolo",
        "canny_people_on_black",
        "canny_people_on_background",
    }:
        yolo = model_hub.detect_yolo(out, _int(sliders_ajax, "confidenceSliderValue"))
        if rendering_mode == "extract_objects_yolo_mode":
            out = extract_objects_yolo(out, yolo)
            out = draw_yolo_stats(out, yolo)
        elif rendering_mode == "text_render_yolo":
            out = objects_to_text_yolo(
                out,
                yolo,
                _int(sliders_ajax, "asciiSizeSliderValue"),
                _int(sliders_ajax, "asciiIntervalSliderValue"),
                _int(sliders_ajax, "rcnnBlurSliderValue"),
                _int(sliders_ajax, "asciiThicknessSliderValue"),
            )
        elif rendering_mode == "canny_people_on_black":
            edges = cv2.Canny(out, 80, 160)
            out = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        elif rendering_mode == "canny_people_on_background":
            edges = cv2.Canny(out, 80, 160)
            edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            out = cv2.addWeighted(out, 0.75, edges, 0.7, 0)
        if "yolo" in model_hub.status_messages:
            out = overlay_status(out, model_hub.status_messages["yolo"])

    elif rendering_mode in {
        "color_objects_on_gray",
        "color_objects_on_gray_blur",
        "color_objects_blur",
        "extract_and_cut_background",
        "extract_and_replace_background",
        "color_canny",
        "color_canny_on_background",
    }:
        rcnn = model_hub.detect_rcnn(out)
        confidence = _int(sliders_ajax, "confidenceSliderValue")
        if rendering_mode == "color_objects_on_gray":
            out = color_objects_on_gray(out, rcnn, confidence)
        elif rendering_mode == "color_objects_on_gray_blur":
            out = color_objects_on_gray(out, rcnn, confidence)
            out = cv2.GaussianBlur(out, (5, 5), 3)
        elif rendering_mode == "color_objects_blur":
            out = blur_background_rcnn(out, rcnn, confidence, _int(sliders_ajax, "rcnnBlurSliderValue"))
        elif rendering_mode == "extract_and_cut_background":
            canny = cv2.Canny(out, 70, 140)
            out = cv2.cvtColor(canny, cv2.COLOR_GRAY2BGR)
            if rcnn is not None:
                out = color_canny_rcnn(out, rcnn, confidence, 3, 30, 90, 1)
        elif rendering_mode == "extract_and_replace_background":
            out = replace_background_rcnn(
                out,
                frame_background,
                rcnn,
                confidence,
                _int(sliders_ajax, "cannyBlurSliderValue"),
                _int(sliders_ajax, "cannyThresSliderValue"),
                _int(sliders_ajax, "cannyThresSliderValue2"),
                _int(sliders_ajax, "lineThicknessSliderValue"),
            )
        elif rendering_mode == "color_canny":
            out = color_canny_rcnn(
                out,
                rcnn,
                confidence,
                _int(sliders_ajax, "cannyBlurSliderValue"),
                _int(sliders_ajax, "cannyThresSliderValue"),
                _int(sliders_ajax, "cannyThresSliderValue2"),
                _int(sliders_ajax, "lineThicknessSliderValue"),
            )
        elif rendering_mode == "color_canny_on_background":
            edges = cv2.Canny(out, 70, 140)
            out = cv2.addWeighted(out, 0.8, cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR), 0.6, 0)
        if "rcnn" in model_hub.status_messages:
            out = overlay_status(out, model_hub.status_messages["rcnn"])

    elif rendering_mode == "caffe_colorization":
        colorized = model_hub.colorize_caffe(out)
        out = colorized if colorized is not None else cv2.cvtColor(cv2.cvtColor(out, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
        if "caffe" in model_hub.status_messages:
            out = overlay_status(out, model_hub.status_messages["caffe"])

    elif rendering_mode == "cartoon_effect":
        out = cartoon_effect(
            out,
            _int(sliders_ajax, "cannyBlurSliderValue"),
            _int(sliders_ajax, "cannyThresSliderValue"),
            _int(sliders_ajax, "cannyThresSliderValue2"),
            _int(sliders_ajax, "lineThicknessSliderValue"),
            _int(sliders_ajax, "colorCountSliderValue"),
            _int(sliders_ajax, "sharpenSliderValue"),
            _int(sliders_ajax, "sharpenSliderValue2"),
            _int(sliders_ajax, "denoiseSliderValue"),
            _int(sliders_ajax, "denoiseSliderValue2"),
        )

    elif rendering_mode == "pencil_drawer":
        out = pencil_drawer(
            out,
            _int(sliders_ajax, "cannyBlurSliderValue"),
            _int(sliders_ajax, "cannyThresSliderValue"),
            _int(sliders_ajax, "cannyThresSliderValue2"),
            _int(sliders_ajax, "lineThicknessSliderValue"),
            _int(sliders_ajax, "sharpenSliderValue"),
            _int(sliders_ajax, "sharpenSliderValue2"),
            _int(sliders_ajax, "denoiseSliderValue"),
            _int(sliders_ajax, "denoiseSliderValue2"),
        )

    elif rendering_mode == "two_colored":
        out = two_colored(
            out,
            _int(sliders_ajax, "sharpenSliderValue"),
            _int(sliders_ajax, "sharpenSliderValue2"),
            _int(sliders_ajax, "denoiseSliderValue"),
            _int(sliders_ajax, "denoiseSliderValue2"),
        )

    elif rendering_mode == "upscale_opencv":
        upscale = model_hub.upscale_superres(out, str(sliders_ajax.get("superresModel") or server_states["superres_model"]))
        out = upscale if upscale is not None else cv2.resize(out, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        out = sharpening(out, _int(sliders_ajax, "sharpenSliderValue"), _int(sliders_ajax, "sharpenSliderValue2"))
        if "superres" in model_hub.status_messages:
            out = overlay_status(out, model_hub.status_messages["superres"])

    elif rendering_mode == "upscale_esrgan":
        upscale = model_hub.upscale_esrgan(out, str(sliders_ajax.get("esrganModel") or server_states["esrgan_model"]))
        out = upscale if upscale is not None else cv2.resize(out, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        out = sharpening(out, _int(sliders_ajax, "sharpenSliderValue"), _int(sliders_ajax, "sharpenSliderValue2"))
        if "esrgan" in model_hub.status_messages:
            out = overlay_status(out, model_hub.status_messages["esrgan"])

    elif rendering_mode == "ascii_painter":
        out = ascii_paint(
            out,
            _int(sliders_ajax, "asciiSizeSliderValue"),
            _int(sliders_ajax, "asciiIntervalSliderValue"),
            _int(sliders_ajax, "asciiThicknessSliderValue"),
            _int(sliders_ajax, "rcnnBlurSliderValue"),
            attach_to_color=True,
        )

    elif rendering_mode == "denoise_and_sharpen":
        out = sharpening(out, _int(sliders_ajax, "sharpenSliderValue"), _int(sliders_ajax, "sharpenSliderValue2"))
        out = denoise(out, _int(sliders_ajax, "denoiseSliderValue"), _int(sliders_ajax, "denoiseSliderValue2"))

    elif rendering_mode == "sobel":
        out = sobel(
            out,
            _int(sliders_ajax, "denoiseSliderValue"),
            _int(sliders_ajax, "denoiseSliderValue2"),
            _int(sliders_ajax, "sharpenSliderValue"),
            _int(sliders_ajax, "sharpenSliderValue2"),
            _int(sliders_ajax, "sobelSliderValue"),
        )

    elif rendering_mode == "boost_fps_dain":
        message = "DAIN legacy CUDA extensions are not loaded; install a modern interpolator adapter for x2/x4/x8 FPS."
        if started_rendering_video:
            out = cv2.addWeighted(out, 0.92, cv2.GaussianBlur(out, (7, 7), 3), 0.08, 0)
        out = overlay_status(out, message)

    out = adjust_br_contrast(out, _int(sliders_ajax, "contrastSliderValue"), _int(sliders_ajax, "brightnessSliderValue"))
    out = adjust_saturation(out, _int(sliders_ajax, "saturationSliderValue"))
    return out


def _int(data: dict, key: str) -> int:
    try:
        return int(data.get(key, 0))
    except (TypeError, ValueError):
        return 0
