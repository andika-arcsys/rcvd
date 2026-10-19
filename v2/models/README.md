# Model (di luar Git)

Berkas bobot tidak disimpan di repositori. GitHub menolak berkas di atas 100 MB, dan `.gitignore` mengabaikan `*.pt` serta `*.onnx`.

Letakkan berkas di mesin yang menjalankan engine, relatif terhadap `models/` (lihat `config/models.yaml`):

```
models/hydrodetect/exp5/model.onnx
models/hydrodetect/exp5/classes.json
models/hydrodetect/exp5/metadata.json
models/hydrodetect/exp5/model.pt      # Ultralytics, dipakai bila berkas ini ada
models/spatialsight/depth_pro.pt      # Apple Depth Pro, Python dan CUDA yang sama
models/spatialsight/model.onnx        # cadangan pratinjau relatif
```

AquaClear tidak memakai berkas ini. HydroDetect menolak muat bila `model.pt` dan `model.onnx` sama-sama tidak ada (`MDL-001`). SpatialSight menolak muat bila `depth_pro.pt` dan `model.onnx` sama-sama tidak ada. Checkpoint Depth Pro didahulukan. Tanpa GPU NVIDIA, keduanya nonaktif (`MDL-003`); Optical dan AquaClear tetap jalan.
