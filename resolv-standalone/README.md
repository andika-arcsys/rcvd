# RESOLV - Image Resolution Lab

Aplikasi web Flask untuk mengubah resolusi gambar secara lokal (0.25x - 4x):

- **Upscale** (>1x) dengan Real-ESRGAN ncnn-vulkan
- **Downscale** (<1x) dengan interpolasi OpenCV `INTER_AREA`
- **Noop** (1x) mengembalikan gambar asli
- UI dark-mode, semua proses berjalan 100% lokal

## Struktur folder

```
.
├── app.py
├── requirements.txt
├── templates/
│   └── index.html
├── models/                 <- taruh file model .param/.bin di sini
├── uploads/                <- otomatis, file yang diunggah
├── outputs/                <- otomatis, hasil proses
└── realesrgan-ncnn-vulkan.exe   <- taruh binary di sini (sejajar app.py)
```

## Setup

### 1. Install dependency Python

```bash
pip install -r requirements.txt
```

### 2. Taruh binary Real-ESRGAN (untuk fitur upscale)

Unduh rilis dari
[Real-ESRGAN-ncnn-vulkan releases](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases),
lalu:

- Salin binary-nya ke folder ini (sejajar `app.py`):
  - Windows: `realesrgan-ncnn-vulkan.exe` (atau `realesrgan.exe`)
  - Linux/macOS: `realesrgan-ncnn-vulkan`
- Salin file model (`.param` + `.bin`) ke folder `models/`
  (lihat `models/PUT_MODELS_HERE.txt` untuk nama file yang benar).

> Downscale (<1x) dan noop (1x) sudah bisa dipakai tanpa binary/model.
> Upscale (>1x) baru berfungsi setelah binary + model tersedia, dan
> membutuhkan GPU yang mendukung Vulkan.

### 3. Jalankan

```bash
python app.py
```

Buka `http://127.0.0.1:5000` di browser.

## Cara pakai

1. Unggah gambar (PNG/JPG/WEBP/BMP, maks 25 MB, maks 2048x2048 px).
2. Geser slider **Skala Target** (0.25x - 4x).
3. Pilih model (untuk upscale).
4. Klik **JALANKAN PROSES**, lalu unduh hasilnya.

## Kredit

UI dan konsep diadaptasi dari [angslhn/RESOLV](https://github.com/angslhn/RESOLV).
Mesin upscale: [Real-ESRGAN-ncnn-vulkan](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan).
