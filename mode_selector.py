"""Rendering primitives shared by the mode dispatcher."""

from __future__ import annotations

from random import randint

import cv2
import numpy as np
from sklearn.cluster import MiniBatchKMeans

from model_adapters import DetectionResult


COLORS_YOLO = np.random.default_rng(46).uniform(0, 255, size=(80, 3))


def overlay_status(frame: np.ndarray, message: str) -> np.ndarray:
    out = frame.copy()
    height, width = out.shape[:2]
    cv2.rectangle(out, (10, height - 48), (min(width - 10, 980), height - 10), (0, 0, 0), -1)
    cv2.putText(out, message, (24, height - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 165, 255), 2)
    return out


def draw_yolo_stats(frame: np.ndarray, result: DetectionResult) -> np.ndarray:
    if not result.indexes:
        return frame
    counts: dict[str, int] = {}
    for index in result.indexes:
        label = _label_for(result, index)
        counts[label] = counts.get(label, 0) + 1
    for row, (label, count) in enumerate(sorted(counts.items()), start=1):
        y = row * 40
        cv2.rectangle(frame, (20, y - 25), (270, y + 11), (0, 0, 0), -1)
        cv2.putText(frame, f"{label}: {count}", (40, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    return frame


def extract_objects_yolo(frame: np.ndarray, result: DetectionResult) -> np.ndarray:
    out = frame.copy()
    for index in result.indexes:
        x, y, w, h = _clamped_box(result.boxes[index], frame)
        label = _label_for(result, index)
        color = _color_for(result.class_ids[index])
        confidence = result.confidences[index]
        overlay = np.zeros_like(out)
        cv2.rectangle(overlay, (x, y), (x + w, y + h), color, -1)
        out = cv2.addWeighted(out, 1.0, overlay, 0.18, 0)
        cv2.rectangle(out, (x, y), (x + w, y + h), (255, 255, 255), 2)
        cv2.putText(
            out,
            f"{label}[{confidence:.2f}]",
            (x, max(20, y - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2,
            lineType=cv2.LINE_AA,
        )
    return out


def objects_to_text_yolo(
    frame: np.ndarray,
    result: DetectionResult,
    font_size: int,
    ascii_distance_value: int,
    blur_value: int,
    ascii_thickness_value: int,
) -> np.ndarray:
    out = frame.copy()
    if not result.indexes:
        return ascii_paint(out, font_size, ascii_distance_value, ascii_thickness_value, blur_value, True)
    for index in result.indexes:
        x, y, w, h = _clamped_box(result.boxes[index], out)
        crop = out[y : y + h, x : x + w]
        if crop.size == 0:
            continue
        out[y : y + h, x : x + w] = ascii_paint(
            crop,
            font_size,
            ascii_distance_value,
            ascii_thickness_value,
            blur_value,
            attach_to_color=False,
        )
    return out


def color_objects_on_gray(frame: np.ndarray, rcnn_result: tuple | None, confidence_value: int) -> np.ndarray:
    gray = cv2.cvtColor(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    if rcnn_result is None:
        return cv2.addWeighted(gray, 0.5, frame, 0.5, 0)
    boxes, masks, labels, _colors = rcnn_result
    out = gray
    for class_id, confidence, start_x, start_y, end_x, end_y, mask in _iter_rcnn_masks(frame, boxes, masks, confidence_value):
        if labels[class_id] in {"person", "car", "truck", "bus", "bicycle"}:
            out[start_y:end_y, start_x:end_x][mask] = frame[start_y:end_y, start_x:end_x][mask]
    return out


def blur_background_rcnn(frame: np.ndarray, rcnn_result: tuple | None, confidence_value: int, blur_value: int) -> np.ndarray:
    blur_value = _odd(max(1, blur_value))
    out = cv2.GaussianBlur(frame, (blur_value, blur_value), blur_value)
    if rcnn_result is None:
        return out
    boxes, masks, _labels, _colors = rcnn_result
    for _class_id, _confidence, start_x, start_y, end_x, end_y, mask in _iter_rcnn_masks(frame, boxes, masks, confidence_value):
        out[start_y:end_y, start_x:end_x][mask] = frame[start_y:end_y, start_x:end_x][mask]
    return out


def color_canny_rcnn(
    frame: np.ndarray,
    rcnn_result: tuple | None,
    confidence_value: int,
    canny_blur: int,
    canny_thres1: int,
    canny_thres2: int,
    line_thickness: int,
) -> np.ndarray:
    blurred = cv2.GaussianBlur(frame, (_odd(canny_blur), _odd(canny_blur)), canny_blur)
    edges = cv2.Canny(blurred, canny_thres1, canny_thres2)
    edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    edges *= np.array((1, 1, 0), np.uint8)
    out = cv2.GaussianBlur(edges, (5, 5), 3)
    if rcnn_result is None:
        return out
    boxes, masks, labels, _colors = rcnn_result
    object_edges = np.zeros_like(frame)
    kernel = np.ones((max(1, line_thickness), max(1, line_thickness)), np.uint8)
    for class_id, _confidence, start_x, start_y, end_x, end_y, mask in _iter_rcnn_masks(frame, boxes, masks, confidence_value):
        color = (0, 255, 0) if labels[class_id] == "person" else (255, 0, 255)
        region = cv2.dilate(edges[start_y:end_y, start_x:end_x], kernel, iterations=1)
        region[np.any(region != 0, axis=2)] = color
        object_edges[start_y:end_y, start_x:end_x][mask] = region[mask]
    return np.bitwise_or(out, object_edges)


def replace_background_rcnn(
    frame: np.ndarray,
    background: np.ndarray | None,
    rcnn_result: tuple | None,
    confidence_value: int,
    canny_blur: int,
    canny_thres1: int,
    canny_thres2: int,
    line_thickness: int,
) -> np.ndarray:
    if background is None:
        background = np.zeros_like(frame)
    background = cv2.resize(background, (frame.shape[1], frame.shape[0]))
    if rcnn_result is None:
        return cv2.addWeighted(frame, 0.45, background, 0.55, 0)
    object_edges = color_canny_rcnn(frame, rcnn_result, confidence_value, canny_blur, canny_thres1, canny_thres2, line_thickness)
    return cv2.addWeighted(object_edges, 1.0, background, 1.0, 0)


def cartoon_effect(
    frame: np.ndarray,
    blur_value: int,
    canny_thres: int,
    canny_thres2: int,
    line_thickness: int,
    color_count: int,
    sharpen: int,
    sharpen2: int,
    denoise_value: int,
    denoise_value2: int,
) -> np.ndarray:
    blurred = cv2.GaussianBlur(frame, (_odd(blur_value), _odd(blur_value)), blur_value)
    edges = cv2.Canny(blurred, canny_thres, canny_thres2)
    edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    kernel = np.ones((max(1, line_thickness), max(1, line_thickness)), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)
    out = frame.copy()
    out[np.where((edges > [0, 0, 0]).all(axis=2))] = [0, 0, 0]
    out = limit_colors_kmeans(out, color_count)
    out = sharpening(out, sharpen, sharpen2)
    out = denoise(out, denoise_value, denoise_value2)
    return cv2.GaussianBlur(out, (3, 3), 1)


def pencil_drawer(
    frame: np.ndarray,
    blur_value: int,
    canny_thres: int,
    canny_thres2: int,
    line_thickness: int,
    sharpen: int,
    sharpen2: int,
    denoise_value: int,
    denoise_value2: int,
) -> np.ndarray:
    out = cartoon_effect(frame, blur_value, canny_thres, canny_thres2, line_thickness, 2, sharpen, sharpen2, denoise_value, denoise_value2)
    return cv2.cvtColor(cv2.cvtColor(out, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)


def two_colored(frame: np.ndarray, sharpen: int, sharpen2: int, denoise_value: int, denoise_value2: int) -> np.ndarray:
    return denoise(sharpening(limit_colors_kmeans(frame, 2), sharpen, sharpen2), denoise_value, denoise_value2)


def sobel(frame: np.ndarray, denoise_value: int, denoise_value2: int, sharpen: int, sharpen2: int, sobel_value: int) -> np.ndarray:
    out = denoise(frame, denoise_value, denoise_value2)
    out = sharpening(out, sharpen, sharpen2)
    grad_x = cv2.Sobel(out, cv2.CV_64F, 1, 0, ksize=_odd(sobel_value))
    grad_y = cv2.Sobel(out, cv2.CV_64F, 0, 1, ksize=_odd(sobel_value))
    out = cv2.addWeighted(grad_x, 0.5, grad_y, 0.5, 0)
    return cv2.convertScaleAbs(out)


def ascii_paint(
    frame: np.ndarray,
    font_size: int,
    ascii_distance_value: int,
    ascii_thickness_value: int,
    blur_value: int,
    attach_to_color: bool,
) -> np.ndarray:
    font_size = max(1, font_size) / 10
    distance = max(1, ascii_distance_value)
    out = cv2.GaussianBlur(frame, (_odd(blur_value), _odd(blur_value)), blur_value)
    canvas = np.zeros_like(out)
    render_str = "abcdefghkmnopqstuwxyz"
    for xx in range(0, out.shape[1], distance):
        for yy in range(0, out.shape[0], distance):
            pixel_b, pixel_g, pixel_r = out[yy, xx]
            if attach_to_color:
                position = min(len(render_str) - 1, int((int(pixel_b) + int(pixel_g) + int(pixel_r)) / 3 / 255 * 20))
                char = render_str[position]
            else:
                char = render_str[randint(0, len(render_str) - 1)]
            cv2.putText(
                canvas,
                char,
                (xx, yy),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_size,
                (int(pixel_b), int(pixel_g), int(pixel_r)),
                max(1, ascii_thickness_value),
                lineType=cv2.LINE_AA,
            )
    return canvas


def sharpening(frame: np.ndarray, sharpening_value: int, sharpening_value2: int) -> np.ndarray:
    if sharpening_value == 0 and sharpening_value2 == 0:
        return frame
    kernel_value = max(1, sharpening_value2)
    kernel = np.array([[-1, -1, -1], [-1, kernel_value + 8, -1], [-1, -1, -1]])
    out = cv2.filter2D(frame, -1, kernel)
    if sharpening_value > 0:
        out = cv2.detailEnhance(out, sigma_s=sharpening_value, sigma_r=0.15)
    return out


def denoise(frame: np.ndarray, denoise_value: int, denoise_value2: int) -> np.ndarray:
    if denoise_value2 <= 0:
        return frame
    return cv2.fastNlMeansDenoisingColored(frame, None, denoise_value2, denoise_value, 7, 15)


def limit_colors_kmeans(frame: np.ndarray, color_count: int) -> np.ndarray:
    if color_count <= 0:
        return frame
    clusters = min(max(2, color_count), 256)
    height, width = frame.shape[:2]
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    flat = lab.reshape((height * width, 3))
    clt = MiniBatchKMeans(n_clusters=clusters, n_init="auto", random_state=46)
    labels = clt.fit_predict(flat)
    quant = clt.cluster_centers_.astype("uint8")[labels].reshape((height, width, 3))
    return cv2.cvtColor(quant, cv2.COLOR_LAB2BGR)


def adjust_saturation(frame: np.ndarray, saturation: int) -> np.ndarray:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (saturation / 100), 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def adjust_br_contrast(frame: np.ndarray, contrast_value: int, brightness_value: int) -> np.ndarray:
    out = cv2.convertScaleAbs(frame, alpha=contrast_value / 100, beta=0)
    hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    v = cv2.add(v, brightness_value)
    return cv2.cvtColor(cv2.merge((h, s, v)), cv2.COLOR_HSV2BGR)


def _iter_rcnn_masks(frame: np.ndarray, boxes: np.ndarray, masks: np.ndarray, confidence_value: int):
    threshold = confidence_value / 100
    height, width = frame.shape[:2]
    for i in range(0, boxes.shape[2]):
        class_id = int(boxes[0, 0, i, 1])
        confidence = float(boxes[0, 0, i, 2])
        if confidence <= threshold:
            continue
        box = boxes[0, 0, i, 3:7] * np.array([width, height, width, height])
        start_x, start_y, end_x, end_y = box.astype("int")
        start_x, start_y = max(0, start_x), max(0, start_y)
        end_x, end_y = min(width, end_x), min(height, end_y)
        if end_x <= start_x or end_y <= start_y:
            continue
        mask = masks[i, class_id]
        mask = cv2.resize(mask, (end_x - start_x, end_y - start_y), interpolation=cv2.INTER_CUBIC) > 0.1
        yield class_id, confidence, start_x, start_y, end_x, end_y, mask


def _clamped_box(box: list[int], frame: np.ndarray) -> tuple[int, int, int, int]:
    height, width = frame.shape[:2]
    x, y, w, h = box
    x = max(0, min(x, width - 1))
    y = max(0, min(y, height - 1))
    w = max(1, min(w, width - x))
    h = max(1, min(h, height - y))
    return x, y, w, h


def _label_for(result: DetectionResult, index: int) -> str:
    class_id = result.class_ids[index]
    if 0 <= class_id < len(result.labels):
        return result.labels[class_id]
    return f"class_{class_id}"


def _color_for(class_id: int) -> tuple[int, int, int]:
    color = COLORS_YOLO[class_id % len(COLORS_YOLO)]
    return int(color[0]), int(color[1]), int(color[2])


def _odd(value: int) -> int:
    value = max(1, int(value))
    return value if value % 2 else value + 1
