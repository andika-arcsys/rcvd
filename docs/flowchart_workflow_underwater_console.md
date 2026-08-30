# Flowchart Workflow — Underwater Drone Inspection Console

File diagram Draw.io (mxGraph): [`flowchart_workflow_underwater_console.xml`](./flowchart_workflow_underwater_console.xml)

## Cara membuka di Draw.io

1. Buka [https://app.diagrams.net](https://app.diagrams.net) (atau desktop Draw.io).
2. **Arrange → Insert → Advanced → XML…** atau **Extras → Edit Diagram**.
3. Tempel seluruh isi file XML, lalu Apply.
4. Alternatif: File → Open dari perangkat, pilih `flowchart_workflow_underwater_console.xml`.

---

## Ringkasan alur operator

```text
ROV rekam pipa
   → video ke PC
   → python web/app.py
   → Browser Live Console (4 layar)
   → (opsional) HydroDetect ON / SpatialSight ON
   → Freeze
   → Kalibrasi biru + cm
   → Ukur (kuning / magenta / oranye)
   → Save snapshot
   → ROI Gallery + keterangan inspector
   → Resume (kalibrasi hilang) → scene berikutnya
```

---

## Checklist fitur (satu per satu)

| # | Fitur UI | Perilaku |
| --- | --- | --- |
| 1 | **Freeze frame** | Bekukan frame; status `FRAME FROZEN`; depth/titik harus same-frame |
| 2 | **Resume live** | Putar lagi; **hapus** calibration `REFERENCE_SCALED` |
| 3 | **Clear points** | Hapus titik tanpa resume |
| 4 | **Layar 1 Optical Native View** | Raw + canvas; **satu-satunya** tempat klik titik |
| 5 | **Layar 2 HydroDetect Engine** | Toggle ON → segmentasi/deteksi; OFF → placeholder + unload |
| 6 | **Layar 3 AquaClear** | Enhancement realtime **selalu aktif** |
| 7 | **Layar 4 SpatialSight** | Toggle ON → depth Turbo relatif; keyframe async |
| 8 | **Blue calibration** | 2 titik + input cm (mis. 76.2) + Save |
| 9 | **Yellow measurement** | 2 titik → jarak 3D **cm** |
| 10 | **Magenta distance** | Tepat 2 titik → `PATH_DISTANCE` **cm** |
| 11 | **Orange area** | ≥3 titik → `SURFACE_AREA` **cm2** |
| 12 | **Save snapshot** | JPEG Optical Native View + JSON metadata |
| 13 | **ROI Gallery** | Thumbnail + metadata + editor keterangan inspector |
| 14 | **Simpan keterangan** | `POST /api/gallery/<id>/notes` → field `inspector_notes` |
| 15 | **System panel** | VRAM, scale, inference state, intrinsics status, logs |
| 16 | **Space** | Shortcut Freeze/Resume |

---

## Empat layar (produk)

| Layar | Nama | Feed | Library inti |
| --- | --- | --- | --- |
| 1 | Optical Native View | `/feed/raw` | OpenCV overlay canvas |
| 2 | HydroDetect Engine | `/feed/yolo` | Ultralytics YOLO + PyTorch CUDA |
| 3 | AquaClear | `/feed/enhanced` | `underwater_enhance.pipeline` (realtime) |
| 4 | SpatialSight | `/feed/depth` | Depth Anything 3 (default) / Depth Pro |

Stream MJPEG di-downscale (`--stream-max-side`, default 640). Klik memakai `x_norm`/`y_norm` (letterbox-aware) ke resolusi penuh.

---

## Keterangan di luar blok flowchart — library & proses

### Stack aplikasi

| Komponen | Library / modul | Peran |
| --- | --- | --- |
| Web UI + API | **Flask** | Route live/gallery, `/api/*`, MJPEG multipart |
| Video I/O & gambar | **OpenCV (`cv2`)** | `VideoCapture`, resize, JPEG, garis/titik, `COLORMAP_TURBO` |
| Numerik | **NumPy** | Depth Float32, back-projection, path/area mesh |
| GPU | **PyTorch + CUDA** | Inferensi HydroDetect & SpatialSight |
| Deteksi | **Ultralytics YOLO** | Backend HydroDetect (`exp-5.pt`, conf 0.7, `retina_masks`) |
| Depth | **Depth Anything 3** (`DA3METRIC-LARGE`) | Backend default SpatialSight (HF) |
| Depth alt. | **Apple Depth Pro** | Opsional via `--depth-backend depth_pro` |
| Enhancement | **`underwater_enhance`** | AquaClear: WB, red compensation, CLAHE, unsharp, temporal EMA |
| Metrologi | **`underwater_enhance.measurement`** | Scale kalibrasi, jarak 3D, path, area, uncertainty, validity |

### Proses internal (tidak terlihat sebagai “tombol”)

1. **`vision-worker` thread** — baca frame, pacing FPS sumber, bangun 4 panel, encode JPEG.
2. **`depth-preview-worker` thread** — SpatialSight keyframe async; tidak menahan playback live.
3. **Lazy load model** — HydroDetect/SpatialSight hanya dimuat saat toggle ON.
4. **Gallery context** — buka `/gallery` → unload model live (anti-OOM, mis. RTX 3070 8GB).
5. **Angka metrik** — selalu dari tensor depth mentah × scale; **bukan** dari warna depth map.
6. **Satuan UI** — jarak **cm**, luas **cm2**.
7. **Persistensi gallery** — `web/data/gallery/{id}.jpg` + `{id}.json` (path absolut dari root repo).

### Status validitas pengukuran

| Status | Arti |
| --- | --- |
| `UNCALIBRATED` | Belum ada referensi pipa/laser |
| `ESTIMATE_ONLY_SAME_FRAME` | Ada kalibrasi same-frame; K underwater belum tervalidasi |
| `VALID_SAME_FRAME` | Same-frame + intrinsics underwater terkalibrasi |
| `INVALID_CROSS_FRAME` | Dicegah: Resume menghapus calibration lama |

### Perintah tipikal

```bat
python web\app.py --source "D:\arcgiz\video 1.mp4" ^
  --model "D:\rcvd\exp-5.pt" --device 0 ^
  --depth-backend depth_anything3 ^
  --stream-max-side 640
```

Buka `http://127.0.0.1:5000` (Live) dan `/gallery` (ROI Gallery).
