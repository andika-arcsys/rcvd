# Uji GPU di PC inspeksi

Mesin pengembangan ini tidak punya GPU NVIDIA. Dua skrip berikut **tidak lulus** di sini (kode keluar 2). Uji akhir HydroDetect dan SpatialSight dijalankan di PC inspeksi.

Dari folder `v2`, dengan lingkungan yang sama seperti engine:

```bash
deepenv/bin/python scripts/gpu_soak_test.py
deepenv/bin/python scripts/eval_hydrodetect.py
```

`gpu_soak_test.py` mengganti fitur 50 kali (AquaClear, dan HydroDetect atau SpatialSight bila berkas ONNX ada), lalu Optical. VRAM dibaca sebelum dan sesudah. Gagal bila pemakaian tidak kembali ke garis dasar ditambah `performance.vram_baseline_tolerance_mb`.

`eval_hydrodetect.py` membutuhkan:

- D-10 `models/hydrodetect/exp5/model.onnx`
- D-12 `models/hydrodetect/exp5/metadata.json`
- D-17 gambar di `samples/labeled/`

Skrip menyalin kunci metadata apa adanya. Skrip tidak menghitung dan tidak mengarang precision, recall, atau mAP.
