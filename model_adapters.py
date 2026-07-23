"""Optional model backends used by the renderer.

Large model files are intentionally not committed. Each adapter checks for
the expected files under ``models/`` and returns a CPU/OpenCV fallback when
the user has not installed a model yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parent
MODELS_DIR = ROOT / "models"


ESRGAN_MODEL_PATHS = {
    "FALCOON": MODELS_DIR / "esrgan" / "falcoon.pth",
    "MANGA": MODELS_DIR / "esrgan" / "Manga109Attempt.pth",
    "RRDB_ESRGAN": MODELS_DIR / "esrgan" / "RRDB_ESRGAN_x4_old_arch.pth",
    "RRDB_PSNR": MODELS_DIR / "esrgan" / "RRDB_PSNR_x4_old_arch.pth",
    "RRDB_INTERP_0.2": MODELS_DIR / "esrgan" / "interp_02.pth",
    "RRDB_INTERP_0.4": MODELS_DIR / "esrgan" / "interp_04.pth",
    "RRDB_INTERP_0.6": MODELS_DIR / "esrgan" / "interp_06.pth",
    "RRDB_INTERP_0.8": MODELS_DIR / "esrgan" / "interp_08.pth",
}


@dataclass
class DetectionResult:
    boxes: list[list[int]]
    class_ids: list[int]
    confidences: list[float]
    indexes: list[int]
    labels: list[str]


class ModelHub:
    def __init__(self, prefer_cuda: bool = True) -> None:
        self.prefer_cuda = prefer_cuda
        self._yolo: tuple[Any, list[str], list[str]] | None = None
        self._rcnn: Any | None = None
        self._caffe: Any | None = None
        self._superres: dict[str, Any] = {}
        self._esrgan: dict[str, tuple[Any, Any]] = {}
        self.status_messages: dict[str, str] = {}

    def yolo_available(self) -> bool:
        return all(
            path.exists()
            for path in (
                MODELS_DIR / "yolo" / "yolov3.weights",
                MODELS_DIR / "yolo" / "yolov3.cfg",
                MODELS_DIR / "yolo" / "coco.names",
            )
        )

    def detect_yolo(self, frame: np.ndarray, confidence_value: int) -> DetectionResult:
        if not self.yolo_available():
            self.status_messages["yolo"] = "YOLO model files missing; using no-op detector."
            return DetectionResult([], [], [], [], self._default_yolo_labels())

        if self._yolo is None:
            labels = self._default_yolo_labels()
            net = cv2.dnn.readNet(
                str(MODELS_DIR / "yolo" / "yolov3.weights"),
                str(MODELS_DIR / "yolo" / "yolov3.cfg"),
            )
            self._configure_dnn_backend(net)
            layer_names = net.getLayerNames()
            unconnected = net.getUnconnectedOutLayers().flatten()
            output_layers = [layer_names[int(i) - 1] for i in unconnected]
            self._yolo = net, output_layers, labels

        net, output_layers, labels = self._yolo
        height, width = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (608, 608), (0, 0, 0), True, crop=False)
        net.setInput(blob)
        detections = net.forward(output_layers)

        threshold = confidence_value / 100
        boxes: list[list[int]] = []
        class_ids: list[int] = []
        confidences: list[float] = []
        for output in detections:
            for detection in output:
                scores = detection[5:]
                class_id = int(np.argmax(scores))
                confidence = float(scores[class_id])
                if confidence <= threshold:
                    continue
                box_width = int(detection[2] * width)
                box_height = int(detection[3] * height)
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                x = int(center_x - box_width / 2)
                y = int(center_y - box_height / 2)
                boxes.append([x, y, box_width, box_height])
                class_ids.append(class_id)
                confidences.append(confidence)

        nms = cv2.dnn.NMSBoxes(boxes, confidences, threshold, 0.3)
        indexes = [int(i) for i in np.array(nms).flatten()] if len(nms) else []
        return DetectionResult(boxes, class_ids, confidences, indexes, labels)

    def rcnn_available(self) -> bool:
        return all(
            path.exists()
            for path in (
                MODELS_DIR / "mask-rcnn" / "frozen_inference_graph.pb",
                MODELS_DIR / "mask-rcnn" / "mask_rcnn_inception_v2_coco_2018_01_28.pbtxt",
                MODELS_DIR / "mask-rcnn" / "object_detection_classes_coco.txt",
            )
        )

    def detect_rcnn(self, frame: np.ndarray) -> tuple[Any, Any, list[str], np.ndarray] | None:
        if not self.rcnn_available():
            self.status_messages["rcnn"] = "Mask R-CNN model files missing; using visual fallback."
            return None

        if self._rcnn is None:
            net = cv2.dnn.readNetFromTensorflow(
                str(MODELS_DIR / "mask-rcnn" / "frozen_inference_graph.pb"),
                str(MODELS_DIR / "mask-rcnn" / "mask_rcnn_inception_v2_coco_2018_01_28.pbtxt"),
            )
            self._configure_dnn_backend(net)
            self._rcnn = net

        labels = (
            MODELS_DIR / "mask-rcnn" / "object_detection_classes_coco.txt"
        ).read_text(encoding="utf-8").strip().splitlines()
        np.random.seed(46)
        colors = np.random.randint(0, 255, size=(len(labels), 3), dtype="uint8")
        blob = cv2.dnn.blobFromImage(frame, swapRB=True, crop=False)
        self._rcnn.setInput(blob)
        boxes, masks = self._rcnn.forward(["detection_out_final", "detection_masks"])
        return boxes, masks, labels, colors

    def colorize_caffe(self, frame: np.ndarray) -> np.ndarray | None:
        model_files = (
            MODELS_DIR / "caffe" / "colorization_deploy_v2.prototxt",
            MODELS_DIR / "caffe" / "colorization_release_v2.caffemodel",
            MODELS_DIR / "caffe" / "pts_in_hull.npy",
        )
        if not all(path.exists() for path in model_files):
            self.status_messages["caffe"] = "Caffe colorizer files missing; using grayscale fallback."
            return None

        if self._caffe is None:
            net = cv2.dnn.readNetFromCaffe(str(model_files[0]), str(model_files[1]))
            self._configure_dnn_backend(net)
            pts = np.load(model_files[2])
            class8 = net.getLayerId("class8_ab")
            conv8 = net.getLayerId("conv8_313_rh")
            pts = pts.transpose().reshape(2, 313, 1, 1)
            net.getLayer(class8).blobs = [pts.astype("float32")]
            net.getLayer(conv8).blobs = [np.full([1, 313], 2.606, dtype="float32")]
            self._caffe = net

        scaled = frame.astype("float32") / 255.0
        lab = cv2.cvtColor(scaled, cv2.COLOR_BGR2LAB)
        resized = cv2.resize(lab, (224, 224))
        lightness = cv2.split(resized)[0] - 50
        self._caffe.setInput(cv2.dnn.blobFromImage(lightness))
        ab = self._caffe.forward()[0, :, :, :].transpose((1, 2, 0))
        ab = cv2.resize(ab, (frame.shape[1], frame.shape[0]))
        lightness = cv2.split(lab)[0]
        colorized = np.concatenate((lightness[:, :, np.newaxis], ab), axis=2)
        colorized = cv2.cvtColor(colorized, cv2.COLOR_LAB2BGR)
        colorized = np.clip(colorized, 0, 1)
        return (255 * colorized).astype("uint8")

    def upscale_superres(self, frame: np.ndarray, model_name: str) -> np.ndarray | None:
        model_map = {
            "EDSR": ("EDSR_x4.pb", "edsr"),
            "LAPSRN": ("LapSRN_x4.pb", "lapsrn"),
            "FSRCNN": ("FSRCNN_x4.pb", "fsrcnn"),
            "FSRCNN_SMALL": ("FSRCNN-small_x4.pb", "fsrcnn"),
        }
        file_name, model_type = model_map.get(model_name, model_map["LAPSRN"])
        model_path = MODELS_DIR / "upscalers" / file_name
        if not model_path.exists() or not hasattr(cv2, "dnn_superres"):
            self.status_messages["superres"] = "OpenCV superres model missing; using bicubic fallback."
            return None

        if model_name not in self._superres:
            sr = cv2.dnn_superres.DnnSuperResImpl_create()
            sr.readModel(str(model_path))
            sr.setModel(model_type, 4)
            self._superres[model_name] = sr
        return self._superres[model_name].upsample(frame)

    def upscale_esrgan(self, frame: np.ndarray, model_name: str) -> np.ndarray | None:
        model_path = ESRGAN_MODEL_PATHS.get(model_name, ESRGAN_MODEL_PATHS["FALCOON"])
        if not model_path.exists():
            self.status_messages["esrgan"] = f"{model_name} ESRGAN weights missing; using bicubic fallback."
            return None

        try:
            import torch
            from ESRGAN import architecture as arch
        except Exception as exc:  # pragma: no cover - optional dependency
            self.status_messages["esrgan"] = f"PyTorch/ESRGAN import failed: {exc}"
            return None

        if model_name not in self._esrgan:
            device = torch.device("cuda" if self.prefer_cuda and torch.cuda.is_available() else "cpu")
            model = arch.RRDB_Net(
                3,
                3,
                64,
                23,
                gc=32,
                upscale=4,
                norm_type=None,
                act_type="leakyrelu",
                mode="CNA",
                res_scale=1,
                upsample_mode="upconv",
            )
            try:
                state = torch.load(model_path, map_location=device, weights_only=True)
            except TypeError:
                state = torch.load(model_path, map_location=device)
            if isinstance(state, dict) and "params" in state:
                state = state["params"]
            model.load_state_dict(state, strict=True)
            model.eval().to(device)
            for parameter in model.parameters():
                parameter.requires_grad = False
            self._esrgan[model_name] = model, device

        model, device = self._esrgan[model_name]
        with torch.inference_mode():
            image = frame.astype(np.float32) / 255.0
            image = torch.from_numpy(np.transpose(image[:, :, [2, 1, 0]], (2, 0, 1))).float()
            image = image.unsqueeze(0).to(device)
            output = model(image).data.squeeze().float().cpu().clamp_(0, 1).numpy()
        output = np.transpose(output[[2, 1, 0], :, :], (1, 2, 0))
        return (output * 255.0).round().astype(np.uint8)

    def _configure_dnn_backend(self, net: Any) -> None:
        if not self.prefer_cuda:
            return
        try:
            net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
            net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
        except cv2.error:
            self.status_messages["opencv_cuda"] = "OpenCV CUDA DNN backend is unavailable; using CPU."

    def _default_yolo_labels(self) -> list[str]:
        path = MODELS_DIR / "yolo" / "coco.names"
        if path.exists():
            return path.read_text(encoding="utf-8").strip().splitlines()
        return ["object"]
