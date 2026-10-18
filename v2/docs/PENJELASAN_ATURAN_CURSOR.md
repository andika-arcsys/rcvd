# Penjelasan aturan Cursor – `deepinsight.mdc`

File `.cursor/rules/deepinsight.mdc` adalah "aturan rumah" untuk AI di Cursor. Karena di kepala file tertulis `alwaysApply: true`, Cursor membaca aturan ini otomatis di **setiap** chat di repo DeepInsight. Anda tidak perlu mengulang aturan ini di setiap prompt.

Dokumen ini menjelaskan isi setiap bagian: apa artinya, mengapa diperlukan, dan contoh penerapannya.

---

## 1. Kepala file (frontmatter)

```
description: Aturan tetap proyek DeepInsight (selalu berlaku)
alwaysApply: true
```

| Baris | Arti |
| --- | --- |
| `description` | Nama singkat aturan yang tampil di menu Rules Cursor. |
| `alwaysApply: true` | Aturan selalu dimuat ke setiap percakapan Agent dan Chat di repo ini. Bila `false`, aturan hanya dipakai saat dipanggil. |

---

## 2. Sumber kebenaran

**Isi aturan:** sebelum menulis kode, Cursor wajib membaca empat sumber:

| No | Sumber | Dipakai untuk |
| --- | --- | --- |
| 1 | SPEC_Fungsional.md | Perilaku setiap window. Bila kode berbeda dengan SPEC, SPEC yang benar. |
| 2 | mockups/*.dc.html | Tampilan: warna, jarak, teks tombol. |
| 3 | flowmap/*.drawio | Alur navigasi bernomor. Setiap perpindahan layar harus ada di flow map. |
| 4 | ARCHITECTURE.md dan DECISIONS.md | Keputusan teknis yang sudah diambil. |

Aturan ini juga menjelaskan cara membaca format mockup: `<sc-for>` adalah perulangan, `<sc-if>` adalah kondisi, `<dc-import name="Nav">` adalah sidebar, dan `{{x}}` adalah nilai dari fungsi `renderVals()`.

**Larangan penting:** jangan menambah fitur di luar SPEC. Bila SPEC tidak jelas, tulis pertanyaan di `docs/OPEN_QUESTIONS.md`, jangan menebak.

**Mengapa:** AI cenderung "berimprovisasi" ketika informasi kurang. Aturan ini memaksa AI berhenti dan bertanya, sehingga kode tetap sesuai desain yang sudah disetujui. Inilah yang membuat Cursor menghasilkan daftar OPEN_QUESTIONS pada Fase 0.

---

## 3. Arsitektur

**Isi aturan:** aplikasi dibagi menjadi empat bagian dengan tugas yang tidak boleh tercampur.

| Bagian | Teknologi | Tugas |
| --- | --- | --- |
| `apps/desktop` | React, TypeScript, Vite, Tailwind | Tampilan di browser. Tidak ada logika AI. |
| `services/engine` | Python 3.12, FastAPI, bawaan 127.0.0.1:8000 | Video, inferensi AI, pengukuran, penyimpanan, dan file statis UI. |
| `packages/shared` | Tipe dari OpenAPI ke TypeScript | Satu definisi data yang dipakai bersama, tidak diduplikasi. |
| `config/thresholds.yaml` | YAML | Semua ambang dan batas. |

**Contoh ambang yang wajib di config, bukan di kode:** uji batang ±3%, dua freeze ≤5 cm, tali ukur ≤2%, batas kritis 9,65 m dan 5,32 m, interval inspeksi 1/2/3 tahun, ambang FPS dan GPU.

**Mengapa:**
- **Browser biasa** dipilih (ADR-016) karena sama dengan versi lama yang terbukti, tanpa Rust dan tanpa installer.
- **Engine Python 3.12** karena ekosistem AI (PyTorch, ONNX, OpenCV) ada di Python. UI React hanya tampilan.
- **Ambang di satu file config** agar tim bisa mengubah nilai tanpa mengubah kode, dan tidak ada angka yang tersebar di banyak tempat.
- Arsitektur tidak boleh diubah tanpa mencatat alasannya di `DECISIONS.md`.

---

## 4. Struktur kode

**Isi aturan:**
- **Satu layar = satu folder**, misalnya `apps/desktop/src/screens/3_4_Canvas/`, berisi `index.tsx`, hooks, dan komponen lokal layar itu.
- **Komponen bersama** di `src/components`: Sidebar, Header, StatusBadge, MeasureCanvas, ConfirmDialog.
- **Logika murni** (geometri, luas, skala, status kalibrasi) berada di `packages/shared` atau `services/engine/measure`, sebagai fungsi tanpa UI dan wajib punya unit test.
- **Batas ukuran:** file maksimal ±300 baris, fungsi maksimal ±50 baris.
- **Bahasa:** nama variabel dan fungsi dalam bahasa Inggris; teks yang dilihat pengguna dalam Bahasa Indonesia lewat `i18n/id.json`.
- **Ketat tipe:** tidak boleh `any` di TypeScript, tidak boleh `except` kosong di Python, type hints wajib.

**Mengapa:** struktur yang seragam membuat siapa pun langsung tahu letak kode sebuah layar. File dan fungsi kecil lebih mudah dibaca dan di-debug. Logika ukur yang dipisah dari UI bisa diuji dengan angka pasti, misalnya memastikan luas bidang cekung benar. Larangan `any` dan `except` kosong mencegah error yang tersembunyi.

---

## 5. Aturan GPU, memori, dan cache

Bagian ini paling menentukan keringanan aplikasi.

| Aturan | Arti praktis |
| --- | --- |
| Hanya **satu** model AI di VRAM | AquaClear, HydroDetect, dan SpatialSight tidak pernah dimuat bersamaan. Semua lewat satu `ModelManager`. |
| Urutan ganti model | Hentikan inferensi → hapus referensi model dan tensor → `gc.collect()` → `torch.cuda.empty_cache()` atau lepas session ONNX → catat VRAM sebelum dan sesudah → baru muat model baru. |
| Kapan model dilepas | Saat window fitur ditutup, saat kembali ke Optical, dan saat muncul Peringatan performa. |
| Cara inferensi | `torch.inference_mode()`, FP16 bila GPU mendukung, batch 1, tidak menyimpan tensor antar frame. |
| Runtime produksi | ONNX Runtime (CUDA/TensorRT) untuk produksi; PyTorch hanya saat pengembangan. |
| Watchdog | Tiap 2 detik memeriksa VRAM dan FPS; lewat ambang → UI menampilkan dialog 3.9. |
| Buffer video | Ring buffer berukuran tetap di RAM; frame lama otomatis dibuang. |
| Cache disk | Folder `cache/` dengan batas ukuran (LRU), dibersihkan saat Penutupan sesi. **Bukti tidak pernah masuk cache** dan tidak pernah dihapus otomatis. |
| UI Gallery | Tidak memuat semua gambar sekaligus (virtualized list + thumbnail kecil); bersihkan object URL dan event listener saat layar ditutup. |

**Mengapa:** penyebab utama aplikasi AI terasa berat adalah VRAM dan RAM yang terus bertambah karena model, tensor, frame, atau cache tidak pernah dilepas. Aturan ini menutup semua jalur kebocoran tersebut.

---

## 6. Integritas bukti

**Isi aturan:**
- Pengukuran selalu dilakukan pada **frame asli**. AquaClear dan overlay hanya tampilan.
- Snapshot berupa file gambar dan JSON dengan ID yang sama, **tidak boleh ditimpa**; koreksi selalu menjadi versi baru.
- Paket sesi ditutup dengan hash **SHA-256**, dan Arsip memeriksa ulang hash itu.
- Semua aksi penting masuk **audit log**: FREEZE, kalibrasi, simpan, keputusan Review, perubahan Pengaturan.

**Mengapa:** hasil inspeksi dipakai untuk keputusan teknik (kajian FEA, interval inspeksi). Bukti harus bisa dibuktikan tidak diubah dan bisa ditelusuri siapa melakukan apa.

---

## 7. Mudah di-troubleshoot

**Isi aturan:**
- **Log terstruktur (JSON)** berisi session_id, layar, aksi, dan durasi. Satu file log per sesi, dirotasi.
- **Setiap error** ditangani di batas modul dan ditampilkan dengan pesan Bahasa Indonesia yang jelas beserta kode, misalnya `GPU-001`.
- **Endpoint diagnosis:** `/health` dan `/diagnostics` menampilkan versi, GPU, VRAM, model aktif, dan ukuran cache.
- **Daftar kode error** di `docs/ERROR_CODES.md`.

**Mengapa:** ketika ada masalah di lapangan, operator cukup melaporkan kode error dan session_id. Teknisi langsung bisa mencari di log dan dokumen tanpa menebak.

---

## 8. Cara kerja Cursor di repo ini

**Isi aturan:**
1. Sebelum mengubah kode, Cursor menyebutkan file SPEC atau mockup yang dirujuk beserta rencana singkat.
2. Satu fase per kali; setelah selesai jalankan lint, typecheck, dan test, lalu ringkas perubahan.
3. Commit kecil dengan pesan jelas, misalnya `feat(screen-3_4): ...` atau `fix(engine-gpu): ...`.
4. Jangan menghapus atau menulis ulang modul yang sudah lulus test tanpa alasan tertulis.

**Mengapa:** perubahan kecil dan teruji mudah ditinjau dan mudah dibatalkan bila salah. Aturan nomor 4 mencegah AI "merapikan" kode yang sudah benar lalu malah merusaknya.

---

## 9. Bagian yang perlu diperbarui

Beberapa isi aturan sudah tertinggal dari keputusan terbaru. Perbarui file `.mdc` agar Cursor tidak bingung:

| Bagian | Tertulis sekarang | Seharusnya |
| --- | --- | --- |
| Sumber kebenaran | Jalur `design/docs`, `design/mockups`, `design/flowmap` | `docs/`, `mockups/`, `flowmap/` di root repo |
| Sumber kebenaran | Urutan prioritas belum ada | ANSWERS_OPEN_QUESTIONS.md dan DECISIONS.md > aturan ini > SPEC > mockup |
| GPU | Ganti model cukup dengan `empty_cache()` | Satu **proses pekerja** per model; bila VRAM belum kembali ke baseline + toleransi dalam batas waktu, proses pekerja dimatikan |
| Integritas bukti | Snapshot = JPEG + JSON | Frame asli **PNG** (lossless) + SHA-256; JPEG dengan overlay hanya untuk laporan |
| Integritas bukti | FREEZE belum dijelaskan | UI hanya mengirim `frame_id`; engine mengambil frame dari ring buffer |
| Logika ukur | Heron | Luas memakai **shoelace** pada koordinat terkalibrasi; Heron hanya cek silang 3 titik |
| Logika ukur | Belum ada | Koordinat node di-undistort dengan file kalibrasi kamera; tanpa file kalibrasi, status maksimal ESTIMATE_ONLY |
