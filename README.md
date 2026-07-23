# PyCameraServer Modern Clone

Repository ini adalah port/clone dari tampilan dan kontrol
[alexfcoding/PyCameraServer](https://github.com/alexfcoding/PyCameraServer) untuk
stack modern:

- Python 3.12
- Flask 3.x
- OpenCV 4.12+
- PyTorch CUDA 13.2 wheel (`cu132`)
- Adapter ESRGAN lama tetap disediakan untuk model RRDB `.pth`

UI lama dipertahankan: halaman mode selector, halaman editor, kode mode huruf
(`a`, `b`, `j`, `t`, `z`, dan seterusnya), slider, AJAX `/settings`, streaming
MJPEG `/video`, `/stats`, START/STOP, screenshot, dan download render.

## Quick start

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Opsional GPU PyTorch CUDA 13.2:
pip install -r requirements-cu132.txt

python main.py -i 0.0.0.0 -o 8000
```

Manual editor launch:

```bash
python editor.py -i 0.0.0.0 -o 8001 -s static/user_uploads/example.jpg -c t -m image
```

## Model folders

Model besar tidak dikomit. Letakkan file dengan nama berikut agar fitur neural
aktif otomatis:

```text
models/
  yolo/
    yolov3.weights
    yolov3.cfg
    coco.names
  mask-rcnn/
    frozen_inference_graph.pb
    mask_rcnn_inception_v2_coco_2018_01_28.pbtxt
    object_detection_classes_coco.txt
  caffe/
    colorization_deploy_v2.prototxt
    colorization_release_v2.caffemodel
    pts_in_hull.npy
  upscalers/
    EDSR_x4.pb
    LapSRN_x4.pb
    FSRCNN_x4.pb
    FSRCNN-small_x4.pb
  esrgan/
    falcoon.pth
    Manga109Attempt.pth
    RRDB_ESRGAN_x4_old_arch.pth
    RRDB_PSNR_x4_old_arch.pth
    interp_02.pth
    interp_04.pth
    interp_06.pth
    interp_08.pth
```

Jika model belum ada, aplikasi tetap berjalan dan menampilkan fallback visual
plus pesan status pada preview.

## Kompatibilitas fitur

| Kode | Mode lama | Status port modern |
| --- | --- | --- |
| `a` | YOLO object extractor | Aktif jika model YOLO ada; fallback no-op dengan status |
| `b` | YOLO ASCII blur | Aktif jika YOLO ada; fallback ASCII frame penuh |
| `j`, `i`, `k`, `m` | Mask R-CNN modes | Aktif jika model Mask R-CNN ada; fallback efek OpenCV |
| `f` | Caffe colorizer | Aktif jika model Caffe ada; fallback grayscale |
| `n` | EDSR/LapSRN/FSRCNN | Aktif jika `.pb` ada; fallback bicubic x4 |
| `t` | ESRGAN/RRDB | Loader RRDB lama dipertahankan; fallback bicubic x4 |
| `e`, `o`, `p`, `q`, `r`, `s` | CPU OpenCV effects | Aktif langsung |
| `z` | DAIN interpolation | UI dipertahankan; legacy CUDA extension diganti placeholder adapter |

## Catatan CUDA 13.2

Gunakan `requirements-cu132.txt` agar PyTorch diambil dari index resmi cu132:

```bash
pip install -r requirements-cu132.txt
python - <<'PY'
import torch
print(torch.__version__, torch.version.cuda, torch.cuda.is_available())
PY
```

OpenCV CUDA tidak tersedia dari wheel `opencv-contrib-python` PyPI standar.
Untuk akselerasi DNN CUDA (YOLO/Mask R-CNN/Caffe via OpenCV), gunakan salah satu:

1. build OpenCV + opencv_contrib dari source terhadap CUDA 13.2 + cuDNN 9, atau
2. wheel CUDA komunitas yang cocok dengan toolkit/driver Anda, lalu pastikan
   `cv2.getBuildInformation()` menampilkan CUDA dan cuDNN.

Backend ini otomatis fallback ke CPU jika `cv2.dnn.DNN_BACKEND_CUDA` tidak
tersedia.

## ESRGAN modern

Port ini mempertahankan arsitektur RRDB lama dari PyCameraServer agar model
FALCOON/MANGA/RRDB lama tetap bisa diload oleh PyTorch baru. Untuk model
Real-ESRGAN modern, install:

```bash
pip install -r requirements-optional-ai.txt
```

Lalu tambahkan adapter baru di `model_adapters.py` jika ingin memakai
`RealESRGAN_x4plus`, face enhancement GFPGAN, atau model `spandrel`.

## Attribution

Template UI dan arsitektur ESRGAN lama berasal dari PyCameraServer. Lisensi
upstream disimpan di `THIRD_PARTY_PYCAMERASERVER_LICENSE`.
