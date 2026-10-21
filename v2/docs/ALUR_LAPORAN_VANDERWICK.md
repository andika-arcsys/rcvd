# Alur laporan Vanderwick

| Butir | Isi |
| --- | --- |
| Nomor | WF-VND-LAP-001 |
| Revisi | 0 |
| Status | Alur operasional. Dikaji terhadap spesifikasi layar 6–10 dan kode yang berjalan. |
| Penerima | Vanderwick |
| Pemilik isi risiko | Pemeriksa teknik |
| Pemilik persetujuan laporan | Ketua tim |
| Pemilik paket bukti | Pengelola data |
| Sumber | `SPEC_Fungsional.md` layar 6–10, `COMPLIANCE.md`, `config/roles.yaml`, `config/risk.yaml`, `config/sustainability.yaml`, `config/thresholds.yaml`, sidebar, dan rute laporan di engine |

Dokumen ini mengatur bagaimana satu misi inspeksi menjadi laporan, status risiko mingguan, dan paket bukti yang dapat diperiksa ulang. Angka risiko tidak dikarang. Bila prosedur atau rumus masih kosong, layar menampilkan kosong.

## Standar yang dipakai untuk mengkaji

Delapan syarat manajemen laporan dipakai sebagai penggaris. Setiap syarat dinilai terhadap perilaku yang ada di aplikasi hari ini.

| Syarat | Maksud | Yang sudah jalan | Yang masih terbuka |
| --- | --- | --- | --- |
| Identitas dan revisi | Setiap laporan punya nomor, revisi, dan status | Nomor `RPT-<misi>-R<n>`, status draf → diperiksa → disetujui | PDF masih templat singkat |
| Satu sumber fakta | Isi laporan lahir dari keputusan Review | Tombol Susun dari Review mengisi temuan terkonfirmasi. Ringkasan dan rekomendasi boleh disunting sebelum kunci | |
| Dua orang pada jenjang | Penyusun dan pemeriksa bukan akun yang sama | Engine menolak tahap berikutnya bila akunnya sama (RPT-001) | Tombol di layar hanya menjalankan tahap draf → diperiksa. Tahap Ketua tim ada di API, belum punya tombol sendiri |
| Kunci setelah setuju | Naskah yang disetujui tidak ditimpa | Status `approved` mengunci baris. Revisi membuat nomor baru dan menaut ke revisi lama | Tombol Setujui dan kirim ke PIMS saat ini membuka layar PIMS. Ia belum memanggil tahap approved |
| Keterlacakan bukti | Kesimpulan dapat diikuti sampai berkas | Paket membawa SHA-256. Arsip menghitung ulang hash saat diperiksa | Hash laporan di kaki pratinjau masih mengikuti paket, bukan sidik naskah PDF |
| Distribusi menurut peran | Yang tidak berwenang tidak membuka modul | Sidebar mengunci menu sesuai `roles.yaml` | |
| Retensi dan salinan | Bukti tidak hanya ada di satu hard drive | Penutupan menyusun paket, menghitung hash, lalu menyalin bila folder unggah terisi | Bila folder unggah kosong, status tetap `pending`. Salinan kedua adalah tugas operasional |
| Status mingguan adalah ringkasan | Rapat minggu tidak menciptakan angka baru | Interval 3 / 2 / 1 tahun sudah tampil dari ambang PR-06-117 | Posisi risiko S dan B belum dihitung. `risk.yaml` masih `complete: false` |

## Alur satu misi

Urutan di bawah adalah jalan resmi untuk Vanderwick. Menu sidebar boleh melompat, tetapi lompatan itu tidak mengganti jenjang.

1. **Misi dan bukti.** Pilot dan ahli ukur merekam di Live Operation. Snapshot yang disimpan membawa frame, skala, dan ketidakpastian. Frame yang belum terkalibrasi tidak menjadi angka resmi.
2. **Review.** Pemeriksa teknik memutuskan kandidat. Konfirmasi memasukkan temuan ke laporan. Tolak menjadi contoh negatif untuk Analisis AI. Ubah kelas masuk antrean pelatihan ulang. Keputusan tidak dihapus. Perubahan menambah catatan baru.
3. **Susun laporan.** Di layar Laporan, peran yang berhak menekan Susun dari Review. Sistem membuat draf `RPT-<misi>-R<n>`. Ringkasan dan rekomendasi disunting, lalu disimpan.
4. **Periksa.** Pemeriksa teknik, dengan akun yang berbeda dari penyusun draf, menekan Tandai diperiksa. Status menjadi `reviewed`.
5. **Setujui.** Ketua tim, dengan akun yang berbeda lagi, menjalankan tahap `approved` lewat API sampai tombol layar tersedia. Laporan terkunci. Suntingan setelah itu ditolak (RPT-002). Perubahan isi hanya lewat Buat revisi, yang membuka draf baru.
6. **Bawa ke PIMS / RBI.** Setelah status approved, Pemeriksa teknik membuka PIMS / RBI. Posisi risiko hanya boleh diisi dari tabel prosedur yang sudah lengkap, lalu dari temuan laporan minggu itu.
7. **Tutup sesi.** Penutupan menghentikan rekaman, menyusun paket `PKG-<sesi>`, menghitung SHA-256, lalu menyalin ke folder unggah bila folder itu terisi. Keluar baru aktif setelah hash ada.
8. **Arsip.** Pengelola data membuka Arsip, menekan Periksa integritas, dan membaca Utuh atau Perlu cek ulang.

## Deliverable

| Kode | Deliverable | Pemilik | Saat terbit | Syarat terima | Tempat |
| --- | --- | --- | --- | --- | --- |
| D1 | Draf laporan `RPT-<misi>-R<n>` | Penyusun di peran Laporan | Setelah Review punya temuan terkonfirmasi | Nomor, revisi, ringkasan, daftar temuan terkonfirmasi | Layar Laporan |
| D2 | Laporan diperiksa | Pemeriksa teknik | Setelah D1 | Akun pemeriksa berbeda dari penyusun. Status `reviewed` | Layar Laporan |
| D3 | Laporan disetujui dan terkunci | Ketua tim | Setelah D2 | Status `approved`, kunci aktif, revisi lama tetap ada | Layar Laporan |
| D4 | PDF laporan | Ketua tim | Setelah D3 | Berkas PDF unduhan dari nomor laporan itu | Tombol Ekspor PDF |
| D5 | Status risiko mingguan | Pemeriksa teknik | Tiap minggu operasi, setelah D3 minggu itu | Lihat bagian berikut. Tidak berisi posisi yang ditebak | Catatan rapat mingguan, lalu layar PIMS bila prosedur sudah lengkap |
| D6 | Usulan interval inspeksi | Pemeriksa teknik menetapkan | Bersama D5 | Low 3 tahun, Low to Moderate 2 tahun, Moderate ke atas 1 tahun. Sistem mengusulkan, pemeriksa menetapkan | Layar PIMS |
| D7 | Paket bukti `PKG-<sesi>` | Pengelola data | Penutupan sesi | Manifest SHA-256. Periksa integritas berakhir Utuh | Hard drive konsol dan folder unggah |
| D8 | Catatan unggah tertunda | Pengelola data | Bila folder unggah kosong | Status `pending` terlihat di Arsip, dan salinan kedua dijadwalkan | Layar Arsip |
| D9 | Antrean label model | Teknisi program | Bila Review menolak atau mengubah kelas | Jumlah label tampil. Pelatihan hanya mengantri, belum melatih sendiri | Layar Analisis AI |
| D10 | KPI keberlanjutan | Ketua tim, dilihat Manajemen | Bulanan, setelah rumus diisi | Jam, biaya, dan emisi terisi dari rumus. Temuan terkonfirmasi terisi dari Review. Tiap angka dapat dibuka ke misi | Layar Sustainability |

D4 hari ini adalah PDF singkat dari nomor, ringkasan, dan rekomendasi. Vanderwick memakai D3 sebagai naskah yang mengikat sampai isi PDF diperluas.

## Status risiko mingguan

Status mingguan adalah satu kalimat risiko untuk segmen yang diperiksa minggu itu, plus daftar yang menggantung. Ia digerakkan dari bawah oleh bukti, lalu ia menggerakkan keputusan di bawahnya. Ia tidak mengukur pipa lagi.

### Yang menggerakkan status (dari lapangan ke atas)

- Temuan yang status antreannya `confirmed` di Review.
- Laporan minggu itu yang sudah `approved`. Laporan yang masih draf tidak menggeser risiko.
- Perbandingan bentang terhadap batas kritis yang sudah ada di ambang: 9,65 m untuk 16 inci dan 5,32 m untuk 8 inci.
- Posisi risiko terakhir S, bila `prior_position` sudah diisi tim di `config/risk.yaml`. Hari ini nilai itu `null`.
- Status paket: `copied` bila folder unggah terisi, `pending` bila salinan masih hanya di konsol.

### Yang digerakkan status (ke bawah)

Urutan di layar PIMS mengikuti urutan ini.

1. **Posisi sebelum (S).** Risiko terakhir yang sudah disimpan. Tampil sebagai tanda hubung selama prosedur belum lengkap.
2. **Posisi setelah (B).** Risiko setelah temuan minggu ini. Engine saat ini selalu mengembalikan kosong. B tidak dihitung selama `complete: false`, dan tidak boleh diisi dengan tebakan.
3. **PoF geohazard.** Mengikuti PR-06-111 setelah tabel `pof` diisi: bentang terhadap batas kritis, ada atau tidaknya mitigasi, lalu kategori PoF.
4. **LoIE dan interval.** Pilihan A–E dari PR-06-117. Interval yang sudah tampil: Low 3 tahun, Low to Moderate 2 tahun, Moderate ke atas 1 tahun. Pemeriksa teknik yang menetapkan, sistem yang mengusulkan.
5. **Arsip paket.** Tombol Simpan risiko dan arsipkan paket bukti masih nonaktif, karena prosedur belum lengkap. Penutupan sesi tetap dapat menyusun paket tanpa tombol itu.
6. **Angka temuan di Sustainability.** Jumlah temuan terkonfirmasi minggu dan bulan itu.
7. **Antrean Analisis AI.** Tolak dan ubah kelas dari Review minggu itu. Status risiko tidak mengubah metrik model.

### Cara mengisi rapat mingguan sementara layar B masih kosong

Selama pesan "Data prosedur belum diisi" masih tampil, risalah minggu Vanderwick memakai kalimat status dan tiga daftar, tanpa koordinat matriks:

- Laporan disetujui minggu ini, disebut dengan nomor `RPT-...`.
- Temuan terkonfirmasi yang belum punya laporan disetujui.
- Paket berstatus Unggah tertunda.

Posisi S dan B ditulis hanya setelah tim mengisi `matrix`, `pof`, `loie`, dan `prior_position`, lalu mengubah `complete` menjadi true. Sumber yang menunggu isian: PR-06-019, PR-06-111, dan PR-06-117.

## Cara kerja sidebar untuk PIMS / RBI

Sidebar adalah menu kiri pada setiap layar kerja. Lebarnya 220 piksel. Tombol di atasnya melipat menu menjadi ikon selebar 64 piksel. Pilihan lipat disimpan di sesi peramban dengan kunci `di.sidebar`, dan hilang bila sesi peramban ditutup.

Dua belas menu, dari atas: Dashboard, Misi, Live Operation, Review, Gallery, Laporan, PIMS / RBI, Analisis AI, Sustainability, Arsip, Pengaturan, Keluar. PIMS / RBI adalah menu ketujuh dan membuka jalur `/pims`. Menu yang sedang dibuka diberi latar terang dan huruf tebal. Di layar PIMS, yang tebal adalah PIMS / RBI. Layar Laporan tetap menandai Laporan, meskipun tombolnya nanti menuju PIMS.

Bagian atas sidebar menampilkan nama aplikasi, misi aktif, dan peran. Bila belum ada misi, tertulis tidak ada misi.

Hak membuka PIMS / RBI ada di `config/roles.yaml`:

| Peran | PIMS / RBI | Laporan | Arsip | Analisis AI | Sustainability |
| --- | --- | --- | --- | --- | --- |
| Ketua tim | penuh | penuh | penuh | lihat | penuh |
| Pemeriksa teknik | penuh | penuh | penuh | lihat | penuh |
| Pengelola data | terkunci | lihat | penuh | terkunci | lihat |
| Teknisi program | terkunci | terkunci | lihat | penuh | lihat |
| Manajemen | terkunci | lihat | lihat | terkunci | lihat |
| Pilot drone | terkunci | terkunci | lihat | terkunci | lihat |
| Ahli ukur | terkunci | lihat | lihat | terkunci | lihat |

Menu terkunci berwarna abu-abu, tidak dapat diklik, dan judulnya menjelaskan tidak ada akses. Bila mesin peran belum terhubung, semua menu terkunci kecuali Keluar, dengan judul menunggu engine.

Keluar bukan tautan biasa. Ia membuka dialog konfirmasi. Bila ada frame beku atau ukuran yang belum disimpan, dialog menawarkan simpan, buang, atau batal. Penutupan sesi sendiri tidak menampilkan sidebar.

Membuka PIMS dari sidebar tidak mengirim laporan dan tidak mengubah posisi risiko. Pengiriman yang sah adalah laporan yang sudah berstatus disetujui. Dari layar PIMS ada tautan Buka paket ke Arsip. Arsip juga punya menu sendiri, jadi Pengelola data dapat memeriksa hash tanpa membuka PIMS.

## Analisis AI

Layar ini untuk Teknisi program. Ketua tim dan Pemeriksa teknik hanya melihat. Isinya memantau HydroDetect dan antrean perbaikan model.

Yang diperlukan agar layar berisi:

- Berkas metrik resmi (`metadata.json` pada folder model). Tanpa berkas itu layar berkata metrik resmi belum ada. Angka tidak diketik di layar.
- Label dari Review: tolak dan ubah kelas menambah antrean. Tombol Mulai pelatihan ulang hanya mencatat antrean dan audit `retrain_queued`. Ia tidak melatih model di tempat.
- Rilis versi lewat Pengaturan, oleh Ketua tim atau Teknisi program. Model baru aktif setelah rilis tercatat. Layar menampilkan nama dan versi rilis terakhir.
- Unduh diagnostik hanya untuk Teknisi program.

Analisis AI tidak menetapkan posisi S, posisi B, atau interval. Ia memakai sisa keputusan Review agar model berikutnya lebih dekat ke kelas yang pemeriksa sudah putuskan.

## Sustainability — yang diperlukan

Layar menampilkan empat KPI dan daftar misi per bulan. Manajemen boleh melihat. Kartu KPI membuka Misi agar angka dapat ditelusuri.

Yang sudah terisi tanpa rumus:

- Temuan terkonfirmasi: jumlah baris Review berstatus `confirmed`.
- Daftar bulan: jumlah misi yang punya tanggal, dikelompokkan `tahun-bulan`.

Yang masih tanda hubung, karena rumus di `config/sustainability.yaml` masih kosong:

- Jam inspeksi (`hours_formula`).
- Biaya dihemat (`cost_formula`).
- Emisi dihindari, dalam tCO₂e (`emission_formula`).

Engine tidak menjalankan teks rumus sebagai kode. Tim mengisi rumus yang disepakati. Sebelum itu layar sengaja menampilkan tanda hubung, bukan nol.

Agar D10 dapat diterbitkan ke Vanderwick, tim perlu menyerahkan empat hal:

1. Sumber jam: jam misi yang diakui, dan apakah waktu transit dihitung.
2. Faktor biaya: biaya inspeksi yang diganti oleh metode ini, dalam satuan yang sama setiap bulan.
3. Faktor emisi: kg atau ton CO₂e per jam atau per misi, plus batas sistem (bahan bakar kapal, mobilisasi, listrik konsol).
4. Periode yang dikunci: bulan kalender, dan misi yang belum ditutup tidak masuk bulan itu.

KPI tidak mengubah risiko pipa. Ia membaca misi dan temuan yang sudah ada.

## Arsip ketika dokumen di hard drive perlu di-backup

Paket tinggal di hard drive konsol pada `packages/PKG-<sesi>/`. Manifest menyebut tiap berkas snapshot dan SHA-256-nya, lalu satu hash paket. Arsip hanya baca. Tidak ada tombol hapus atau ubah.

Salinan kedua terjadi hanya bila Pengaturan punya lokasi unggah. Penutupan lalu menyalin seluruh folder paket ke lokasi itu dan status menjadi `copied`. Bila lokasi unggah kosong, status di Arsip adalah Unggah tertunda (`pending`). Pada keadaan itu hard drive konsol adalah satu-satunya salinan.

Backup dilakukan bila salah satu syarat ini muncul:

- Status paket `pending`.
- Hard drive konsol akan dipindah, dihapus, atau dipakai ulang untuk misi lain.
- Periksa integritas mengembalikan Perlu cek ulang.
- Laporan yang sudah disetujui belum ada di dalam paket yang Utuh.

Urutan salinan:

1. Biarkan paket di konsol. Jangan menghapus sumber sebelum salinan diperiksa.
2. Isi lokasi unggah di Pengaturan (Ketua tim atau Teknisi program). Perubahan lokasi masuk audit.
3. Tutup sesi lagi hanya untuk sesi yang belum punya paket. Paket yang sudah ada tidak disusun ulang. Untuk paket `pending` yang sudah tersimpan, salin folder `PKG-<sesi>` beserta `manifest.json` ke disk kedua.
4. Di Arsip, tekan Periksa integritas. Utuh berarti hash berkas sama dengan manifest dan sama dengan hash yang tercatat di basis data. Perlu cek ulang berarti ada berkas yang hilang atau berbeda. Laporkan ke Pengelola data dan jangan pakai salinan itu sebagai arsip resmi.
5. Simpan disk kedua di luar konsol lapangan. Nama folder tetap `PKG-<sesi>` supaya hash dapat dihitung ulang dengan cara yang sama.
6. Hapus salinan di konsol hanya setelah salinan luar berstatus Utuh dan risalah minggu mencatat nomor paketnya.

PDF laporan dan diagnostik yang diunduh ke laptop ikut aturan yang sama: mereka salinan kerja. Yang mengikat untuk audit adalah paket ber-hash di Arsip, ditambah laporan terkunci di basis data.

## Batas dokumen ini

Alur di atas adalah cara Vanderwick menjalankan laporan dengan aplikasi yang ada. Posisi B, tombol simpan risiko, rumus jam biaya emisi, dan tombol layar untuk persetujuan Ketua tim masih menunggu pekerjaan berikutnya. Sampai bagian itu ada, risalah mingguan tidak menulis koordinat matriks.
