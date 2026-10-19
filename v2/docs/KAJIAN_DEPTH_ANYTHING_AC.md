# Kajian: gradasi SpatialSight dan Depth Anything at Any Condition

Sumber gambar pembanding: penampil Depth Anything 3 yang sudah dijalankan, dan figur makalah Sun dkk., *Depth Anything at Any Condition*, arXiv:2507.01634 (2025), kode `HVision-NKU/DepthAnythingAC`. Angka di bawah disalin dari Tabel 2 makalah itu (akurasi pasangan DA-2K, encoder ViT-S, lebih tinggi lebih baik).

## Yang terlihat di layar

Log `SpatialSight: cuda ... process_res=504 model=depth-anything/DA3METRIC-LARGE` berarti model sudah menghitung. Dua lintasan di log (0,62 detik lalu 0,09 detik, bentuk `1×3×504×504` dan `1×3×280×504`) adalah inferensi, bukan kegagalan.

Warna hijau–magenta bukan keluaran Depth Anything. Overlay lama mengisi piksel dengan `rgb(jauh, dekat, 120)`. Dekat menjadi hijau, jauh menjadi ungu. Kisi pratinjau juga hanya 64 piksel pada sisi terpanjang, lalu diregangkan ke video, sehingga batas objek hilang.

Konsol lama di `web/app.py` fungsi `_colorize_depth` memakai OpenCV Turbo: persentil 2 dan 98, dekat dipetakan ke ujung hangat, jauh ke ujung dingin. Penampil Depth Anything dan figur makalah memakai keluarga yang sama (Turbo atau `Spectral_r`): objek dekat merah–kuning, latar jauh biru–ungu, batas objek tetap terbaca. SpatialSight sekarang mengikuti fungsi konsol itu dan mengirim JPEG sampai sisi 640. Angka panjang tetap tidak diambil dari layar ini.

## Arti baris log yang lain

| Baris | Arti | Tindakan |
| --- | --- | --- |
| `unauthenticated requests to the HF Hub` | Unduhan tanpa token. Bobot sudah sampai. | Biarkan. Token hanya menaikkan kuota. |
| `xFormers can't load C++/CUDA extensions` | Roda xFormers dibuat untuk torch 2.10 dan Python 3.10. `deepenv` memakai torch 2.13.0+cu132 dan Python 3.12. | Jangan memasang ulang xFormers. Perhatian efisien mati; inferensi tetap jalan. |
| `No module named 'triton'` | Penghitung FLOP. Triton tidak dipasang di Windows ini. | Abaikan. |
| `Dependency gsplat is required for rendering 3DGS` | Cabang Gaussian splat, bukan peta kedalaman dan bukan estimasi dua titik. | Jangan memasang `gsplat`. |

## Apa yang diukur makalah itu

DepthAnything-AC adalah fine-tune Depth Anything V2, bukan Depth Anything 3. Pelatihan menambah 540 ribu gambar tanpa label. Dua mekanisme:

1. Konsistensi tanpa pengawasan: keluaran pada gambar yang dirusak (gelap, cuaca, distorsi sensor) harus dekat dengan keluaran pada gambar asalnya.
2. Spatial Distance Constraint: jarak antar-petak pada bidang gambar digabung dengan selisih disparitas, lalu selisih peta jarak itu dihukum. Tujuannya batas semantik yang lebih tajam, bukan skala meter.

Metrik utamanya akurasi urutan pasangan titik (DA-2K), bukan AbsRel dalam meter pada air. Pada ViT-S:

| Kondisi | Depth Anything V2 | DepthAnything-AC | Selisih |
| --- | --- | --- | --- |
| DA-2K bersih | 0,952 | 0,953 | +0,001 |
| Gelap | 0,910 | 0,923 | +0,013 |
| Kabut | 0,922 | 0,929 | +0,007 |
| Salju | 0,880 | 0,892 | +0,012 |
| Blur | 0,862 | 0,880 | +0,018 |

Pada Robotcar-night makalah menyebut kenaikan δ1 sebesar 0,037 terhadap V2. Tidak ada baris underwater, atenuasi air, atau port kamera. Kabut atmosfer tidak sama dengan turbiditas.

## Peta ke slide infografik

| Langkah slide | Yang dipakai sekarang | Peran DepthAnything-AC |
| --- | --- | --- |
| Video ROV mentah | Frame asli, piksel tidak digeser | Tidak mengubah sumber bukti |
| Pra-proses | AquaClear model terpisah, satu GPU pada satu waktu | Bukan bagian AC |
| Model kedalaman | `depth-anything/DA3METRIC-LARGE`, `process_res` 504, CUDA, anggaran 6144 MB / 90% | AC adalah V2 relatif. Mengganti DA3 berarti melepas kepala metrik DA3 |
| Peta kedalaman | Pratinjau Turbo relatif. Bukan meter | Figur makalah juga relatif. Spectral/Turbo hanya warna |
| Konversi 3D | Frame beku, fokus kosong, skala referensi pada frame yang sama | AC tidak memberi matriks K |
| Ukur dan validitas | Angka 2D tetap skala piksel. Estimasi 3D tidak ditulis ke `span_m` | AC tidak menaikkan status ke VALID |

## Keputusan

Pertahankan DA3METRIC-LARGE untuk estimasi pada frame beku. Warna live mengikuti Turbo konsol supaya operator melihat batas objek seperti figur Depth Anything.

DepthAnything-AC layak diuji nanti sebagai pembanding ketahanan pada frame ROV yang gelap atau buram, pada frame beku yang sama, dengan skala referensi yang sama. Sebelum uji itu, keluarannya tidak masuk angka tersimpan. Bobotnya berkas `.pth` encoder V2 (`vits` / `vitb` / `vitl`), bukan `DA3METRIC-LARGE`, dan tidak dipasang di `deepenv` sekarang.
