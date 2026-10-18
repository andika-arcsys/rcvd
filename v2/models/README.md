# Model (di luar Git)

Berkas bobot tidak disimpan di repositori. GitHub menolak berkas di atas 100 MB, dan `.gitignore` mengabaikan `*.pt` serta `*.onnx`.

Letakkan berkas di mesin yang menjalankan engine, relatif terhadap `models/` (lihat `config/models.yaml`):

```
models/hydrodetect/exp5/model.onnx
models/hydrodetect/exp5/classes.json
models/hydrodetect/exp5/metadata.json
models/hydrodetect/exp5/model.pt      # sumber pelatihan, tidak dimuat saat operasi
models/spatialsight/model.onnx        # Depth Anything V2 Small
```

AquaClear tidak memakai berkas ini. Tanpa `model.onnx`, HydroDetect dan SpatialSight menolak muat dengan kode `MDL-001`. Tanpa GPU NVIDIA, keduanya nonaktif (`MDL-003`); Optical dan AquaClear tetap jalan.
