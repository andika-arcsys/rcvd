"""Shared render state and compatibility mappings for the PyCameraServer clone.

The old project exchanged compact one-letter mode codes with the browser.
Those codes are preserved so the copied templates and controls behave the
same while the backend can evolve independently.
"""

from __future__ import annotations

from copy import deepcopy


UPLOAD_FOLDER = "static/user_uploads"
RENDER_FOLDER = "static/user_renders"

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "mp4",
    "avi",
    "m4v",
    "webm",
    "mkv",
}

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}
VIDEO_EXTENSIONS = {"gif", "mp4", "avi", "m4v", "webm", "mkv"}


render_modes_dict = {
    "canny_people_on_background": "d",
    "canny_people_on_black": "c",
    "extract_and_replace_background": "i",
    "extract_and_cut_background": "g",
    "color_canny": "j",
    "color_canny_on_background": "h",
    "color_objects_on_gray_blur": "l",
    "color_objects_blur": "m",
    "color_objects_on_gray": "k",
    "caffe_colorization": "f",
    "cartoon_effect": "e",
    "extract_objects_yolo_mode": "a",
    "text_render_yolo": "b",
    "denoise_and_sharpen": "o",
    "sobel": "p",
    "ascii_painter": "q",
    "pencil_drawer": "r",
    "two_colored": "s",
    "upscale_opencv": "n",
    "upscale_esrgan": "t",
    "boost_fps_dain": "z",
}

mode_code_to_name = {value: key for key, value in render_modes_dict.items()}


DEFAULT_STATES = {
    "view_source": False,
    "source_image": "",
    "source_url": "",
    "source_mode": "",
    "output_file_page": "",
    "screenshot_path": "",
    "need_to_create_screenshot": False,
    "screenshot_ready": False,
    "working_on": True,
    "frame_processed": 0,
    "total_frames": 0,
    "options": "",
    "screenshot_lock": False,
    "video_reset_lock": False,
    "video_stop_lock": False,
    "mode_reset_lock": False,
    "source_lock": False,
    "render_mode": "a",
    "superres_model": "LAPSRN",
    "esrgan_model": "FALCOON",
}


DEFAULT_SETTINGS = {
    "viewSource": False,
    "cannyBlurSliderValue": 5,
    "cannyThresSliderValue": 71,
    "cannyThresSliderValue2": 21,
    "cannyThres2": 50,
    "saturationSliderValue": 100,
    "contrastSliderValue": 100,
    "brightnessSliderValue": 0,
    "positionSliderValue": 1,
    "confidenceSliderValue": 20,
    "lineThicknessSliderValue": 1,
    "denoiseSliderValue": 7,
    "denoiseSliderValue2": 10,
    "sharpenSliderValue": 0,
    "sharpenSliderValue2": 0,
    "rcnnSizeSliderValue": 10,
    "rcnnBlurSliderValue": 9,
    "sobelSliderValue": 3,
    "asciiSizeSliderValue": 4,
    "asciiIntervalSliderValue": 10,
    "asciiThicknessSliderValue": 1,
    "resizeSliderValue": 100,
    "colorCountSliderValue": 0,
    "videoResetCommand": False,
    "videoStopCommand": False,
    "modeResetCommand": False,
    "screenshotCommand": False,
    "urlSourceResetCommand": False,
    "urlSource": "default",
    "mode": "a",
    "superresModel": "LAPSRN",
    "esrganModel": "FALCOON",
}


settings_ajax = deepcopy(DEFAULT_SETTINGS)
states_dict = deepcopy(DEFAULT_STATES)
