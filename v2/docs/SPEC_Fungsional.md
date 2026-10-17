# Spesifikasi Fungsional Mockup DeepInsight

Oct 17, 2026 · @andika pratama

## Pendahuluan

Dokumen ini mendefinisikan tujuan, tata letak, fitur, cara kerja, aturan, dan alur keluar-masuk setiap window pada mockup DeepInsight. Dokumen ini menjadi acuan pengembang, penguji, dan juri untuk memahami bagaimana aplikasi inspeksi bawah air Van Der Wick bekerja dari awal sesi sampai arsip.

**Acuan yang dipakai**

- Mockup canvas "Mockup DeepInsight D1" (24 layar + komponen sidebar).
- Flow map draw.io v2: halaman 1 navigasi global, halaman 2 Live Operation, halaman 3 task flow free span.
- Skenario operator free span Sinorang v3 dan manual kerja console V2.
- Prosedur JOB Tomori PR-06-019 (matriks risiko), PR-06-111 (geohazard), PR-06-117 (efektivitas dan interval inspeksi).

**Struktur penjelasan setiap window**

1. Tujuan dan pengguna.
2. Masuk dari dan keluar ke (merujuk kode layar flow map).
3. Tata letak.
4. Fitur dan cara kerja.
5. Aturan, validasi, dan kondisi gagal.

**Daftar window**

| Kode | Window | Kompleksitas |
| --- | --- | --- |
| 0 / 0.1 / 0.2 | Splash, Login, Pilih peran | Standar |
| 1 / 2 | Dashboard, Misi & pre-check | Standar |
| 3 | Optical Native View | **Kompleks** |
| 3.0 / 3.9 | Dialog ganti window, Peringatan performa | Standar |
| 3.1 / 3.2 / 3.3 | AquaClear, HydroDetect, SpatialSight | Standar–menengah |
| 3.4 | Canvas ukur & anotasi | **Kompleks** |
| 3.5 / 3.5.3 | Mode Snapshot, Simpan snapshot | **Kompleks** / standar |
| 5 / 5.2 | Gallery, Kalkulator span | Standar / **Kompleks** |
| 4 | Review & Adjudikasi | **Kompleks** |
| 6–12 | Laporan, PIMS/RBI, Analisis AI, Sustainability, Arsip, Pengaturan, Penutupan | Standar |

Semua angka contoh di mockup ditulis sebagai placeholder, misalnya \[x,xx\] m. Angka yang berasal dari prosedur atau skenario (batas kritis 9,65 m dan 5,32 m, uji batang ±3%, dua freeze ≤5 cm, tali ukur ≤2%, interval 1/2/3 tahun) dipakai apa adanya.

## Kerangka bersama

Semua layar kerja memakai satu kerangka yang sama agar operator tidak perlu belajar ulang ketika berpindah modul. Kerangka ini terdiri dari sidebar global, area kepala layar, dan area kerja.

### Sidebar global (komponen Nav)

Sidebar selebar 220 px berada di kiri pada setiap layar kerja. Bagian atasnya menampilkan nama aplikasi, misi aktif, dan peran pengguna. Di bawahnya ada 12 menu: Dashboard, Misi, Live Operation, Review, Gallery, Laporan, PIMS / RBI, Analisis AI, Sustainability, Arsip, Pengaturan, dan Keluar. Menu layar yang sedang dibuka tersorot dengan latar lebih terang dan huruf tebal. Sidebar adalah inti konsep hub and spoke: modul mana pun dapat dibuka langsung tanpa harus melewati urutan tertentu. Layar turunan menyorot menu induknya; contohnya Mode Snapshot dan Canvas menyorot Live Operation, sedangkan Kalkulator span menyorot Gallery. Menu yang tidak diizinkan untuk peran tertentu tampil abu-abu dan tidak dapat diklik.

Layar yang sengaja tanpa sidebar adalah layar sebelum masuk (Splash, Login, Pilih peran), dialog pop-up (Ganti window, Peringatan performa, Simpan snapshot), dan Penutupan sesi. Setiap layar tersebut tetap memiliki tombol lanjut atau kembali yang jelas.

### Tombol kembali dan breadcrumb

Layar turunan memiliki tombol kembali di kiri atas: "← Optical" pada Snapshot dan Canvas, "← Gallery" pada Kalkulator span, dan "← Kembali" pada Review. Breadcrumb di sampingnya menunjukkan posisi, misalnya "Gallery › Kalkulator span".

### Aturan satu window fitur aktif

Di Live Operation hanya satu fitur AI (AquaClear, HydroDetect, atau SpatialSight) boleh aktif. Setiap perpindahan fitur melewati dialog 3.0 yang melepas model sebelumnya dari GPU, lalu memuat model baru. Aturan ini menjaga konsol tetap ringan dan FREEZE tetap responsif.

### Bahasa warna

| Warna | Arti |
| --- | --- |
| Oranye | Aksi utama, FREEZE, frame terkunci |
| Hijau | Lolos, VALID, aman |
| Kuning | Perlu perhatian, ESTIMATE\_ONLY, perlu ulang |
| Merah | Kritis, gagal, UNCALIBRATED, DEPTH\_EDGE\_RISK |
| Biru | Informasi, garis ukur panjang, tautan |

Warna tidak pernah menjadi satu-satunya penanda: setiap status juga ditulis dengan kata.

## Window masuk

### 0 – Splash dan cek sistem

**Tujuan.** Memastikan konsol siap dipakai sebelum operator masuk, sehingga masalah perangkat ditemukan di darat, bukan saat ROV sudah di dalam air.

**Masuk dari / keluar ke.** Layar pertama saat aplikasi dibuka; keluar ke 0.1 Login (flow map halaman 1, garis 1).

**Tata letak dan fitur.** Di tengah layar tampil nama aplikasi, versi aplikasi, dan versi model HydroDetect yang aktif (exp-5). Di bawahnya ada kotak cek sistem otomatis berisi empat butir: GPU tersedia, ruang penyimpanan cukup, jam tersinkron, dan kamera ROV terhubung. Setiap butir menampilkan status OK (hijau), menunggu (kuning), atau gagal (merah), dengan batang progres keseluruhan.

**Cara kerja.** Pemeriksaan berjalan otomatis berurutan. Bila semua lolos, tombol "Sistem siap · Lanjut" aktif. Bila GPU tidak tersedia, operator masih bisa memilih "Lanjut mode terbatas"; pada mode ini HydroDetect dan SpatialSight dinonaktifkan, sedangkan Optical, AquaClear ringan, Snapshot, dan pengukuran tetap tersedia. Jam yang tidak tersinkron harus diperbaiki karena waktu dipakai di metadata snapshot dan hash paket bukti.

### 0.1 – Login

**Tujuan.** Mengidentifikasi pengguna agar setiap aksi, ukuran, dan keputusan tercatat atas nama orang yang benar.

**Masuk dari / keluar ke.** Dari Splash atau dari Penutupan sesi (garis 27); keluar ke 0.2 Pilih peran (garis 2).

**Fitur dan cara kerja.** Dua cara masuk: tombol "Masuk dengan SSO" untuk akun perusahaan saat ada jaringan, dan PIN lapangan enam digit beserta ID pengguna untuk lokasi tanpa jaringan. PIN lapangan diverifikasi terhadap daftar pengguna yang tersimpan di konsol dan disinkronkan ulang saat jaringan tersedia.

**Aturan.** Setelah beberapa kali gagal, akun dikunci sementara dan kejadiannya dicatat di audit log. Jumlah percobaan dan lama penguncian ditetapkan di Pengaturan oleh administrator. Kata sandi atau PIN tidak pernah ditampilkan dan tidak disimpan dalam log.

### 0.2 – Pilih peran dan perangkat

**Tujuan.** Menetapkan peran sesi dan perangkat yang dipakai, sehingga menu dan hak aksi sesuai tanggung jawab.

**Masuk dari / keluar ke.** Dari Login; keluar ke 1 Dashboard (garis 3).

**Fitur.** Enam kartu peran sesuai skenario free span: Ketua tim (semua menu dan persetujuan laporan), Pilot drone (Live Operation, FREEZE, tandai temuan), Ahli pengukuran (Snapshot, kalibrasi, Kalkulator span), Pengelola data (Gallery, Arsip, ekspor), Teknisi program (Analisis AI, rilis model, Pengaturan), dan Pemeriksa teknik (Review, Laporan, PIMS/RBI). Di bawahnya ada pilihan perangkat ROV dan preset kamera yang terkunci.

**Cara kerja dan aturan.** Peran yang dipilih menentukan menu sidebar yang aktif. Satu pengguna dapat memegang lebih dari satu peran bila ditetapkan administrator, tetapi keputusan temuan kritis tetap memerlukan dua pemeriksa yang berbeda. Preset kamera dikunci (fokus dan eksposur) agar kalibrasi tidak berubah selama sesi.

## Dashboard dan Misi

### 1 – Dashboard

**Tujuan.** Memberi gambaran kondisi seluruh misi dalam satu layar dan mengarahkan pengguna ke pekerjaan yang paling mendesak.

**Masuk dari / keluar ke.** Dari Pilih peran, dari sidebar, atau dari Pengaturan setelah simpan. Keluar ke Live Operation (garis 16 “Lanjutkan misi”), Review, Gallery, Kalkulator span, Laporan, dan Misi.

**Tata letak dan fitur.**

- **Baris kepala:** sapaan pengguna, judul, dan tombol oranye "Lanjutkan misi aktif" yang langsung membuka Optical Native View pada misi berjalan.
- **Empat kartu KPI:** misi aktif, temuan menunggu review, snapshot hari ini, dan span terpanjang terukur beserta batas 9,65 m. Tiga kartu terakhir dapat diklik dan membuka layar sumbernya.
- **Banner peringatan prioritas (merah):** muncul bila ada kondisi yang butuh keputusan, misalnya free span mendekati batas kritis. Tautan "Buka di Review" membawa langsung ke kandidat tersebut.
- **Tabel misi terakhir:** nama misi, pipa, tanggal, status (Berjalan, Selesai, Direncanakan), dan tautan aksi sesuai status.

**Aturan.** Angka KPI dihitung dari data sesi dan diperbarui setiap kali Dashboard dibuka. Banner prioritas hanya muncul untuk temuan kritis (Leakage atau span ≥ ambang peringatan) dan hilang setelah temuan diputuskan di Review.

### 2 – Misi dan pre-check

**Tujuan.** Merencanakan misi dan memastikan semua prasyarat Fase K terpenuhi sebelum ROV masuk air.

**Masuk dari / keluar ke.** Dari sidebar, Dashboard, atau Sustainability (garis 24). Keluar ke Optical Native View melalui "Mulai misi" (garis 17).

**Tata letak dan fitur.**

- **Panel rencana:** lokasi, tanggal survei, pilihan diameter pipa, dan daftar tim berisi enam peran. Memilih 16 inci otomatis menetapkan batas kritis 9,65 m; memilih 8 inci menetapkan 5,32 m. Nilai ini kemudian dipakai Kalkulator span dan Review.
- **Panel pre-check (Fase K):** uji batang 1 m dengan toleransi ±3%, kalibrasi lensa, preset kamera terkunci, laser referensi menyala, dan ruang simpan cukup. Setiap butir berstatus Lolos atau Gagal.

**Cara kerja.** Ahli pengukuran mengambil gambar batang 1 m, sistem menghitung panjang terukur, lalu membandingkannya dengan 1 m. Bila selisih melebihi 3%, butir gagal dan operator diarahkan memeriksa laser dan mengulang kalibrasi (sesuai gerbang GK, halaman 3 garis 2).

**Aturan.** Tombol "Mulai misi" hanya aktif bila semua pre-check lolos. Rencana misi tersimpan sebagai draf dan dapat diubah sebelum misi dimulai; setelah dimulai, diameter pipa dan batas kritis terkunci untuk misi tersebut.

## 3 – Optical Native View

**Tujuan.** Optical Native View adalah pusat Live Operation dan satu-satunya sumber bukti asli. Layar ini menampilkan video kamera ROV tanpa pengolahan apa pun, sehingga apa yang dilihat operator sama dengan apa yang direkam. Semua fitur AI (AquaClear, HydroDetect, SpatialSight) dan Canvas dibuka dari sini, dan semua alur kembali ke sini. Karena operator bekerja sambil mengendalikan ROV di arus sungai, layar ini dirancang agar aksi terpenting dapat dilakukan dengan satu tombol dan tanpa mencari-cari.

**Pengguna.** Pilot drone sebagai pengguna utama; Ahli pengukuran dan Ketua tim mengamati dan memberi arahan.

**Masuk dari / keluar ke.** Masuk dari Dashboard (garis 16), Misi (garis 17), sidebar, dialog 3.0 saat Batal (halaman 2 garis 11), setiap window fitur saat "Kembali ke Optical", Mode Snapshot saat RESUME (garis 26), Simpan snapshot saat "Frame selesai" (garis 34), dan Kalkulator span saat selisih melebihi batas (garis 39). Keluar ke dialog 3.0 (garis 1–3), Canvas (garis 4), Mode Snapshot melalui FREEZE (garis 5), Review melalui Tandai temuan (garis 6), dan Penutupan sesi (garis 7).

**Tata letak.**

1. **Header telemetri** di atas: indikator REC berwarna merah, kedalaman (m), heading (derajat), baterai (%), beban GPU (%), dan jam. Telemetri selalu terlihat agar pilot tidak perlu berpindah layar untuk memantau ROV.
2. **Bilah tab fitur** di bawah header: Optical (F1), AquaClear (F2), HydroDetect (F3), SpatialSight (F4), dan Canvas (F5). Tab Optical aktif secara bawaan. Keterangan di kanan bilah mengingatkan bahwa hanya satu window fitur yang aktif dan model lain dilepas otomatis.
3. **Zona video utama** (sekitar 70% lebar area kerja). Di pojok kiri atas tampil frame ID dan timecode; di pojok kanan atas label "Video asli · tanpa pengolahan". Kotak bantu putus-putus di tengah membantu membingkai pipa. Penanda titik laser muncul bila dua titik laser terdeteksi, dan pesan kecil di kiri bawah menyatakan "2 titik laser terdeteksi".
4. **Panel kanan** dengan tiga kartu: kualitas citra (indikator kekeruhan rendah, sedang, tinggi beserta saran tindakan), posisi survei (diameter pipa, batas kritis, segmen aktif dari P0 ke PE+2, jumlah snapshot sesi), dan daftar temuan sesi beserta prioritasnya.
5. **Bilah aksi bawah:** tombol FREEZE berwarna oranye dan paling besar, Tandai temuan, Ganti fitur, dan Selesai sesi di sisi kanan dengan warna merah lembut.

**Fitur dan cara kerja.**

- **FREEZE.** Menekan FREEZE (spasi di keyboard atau tombol A di kontroler) mengunci frame yang sedang tampil beserta frame ID, waktu, kedalaman, dan preset aktif, lalu membuka Mode Snapshot. FREEZE selalu mengambil frame asli, bukan frame hasil AquaClear atau overlay AI. Pemetaan tombol kontroler adalah usulan dan disesuaikan dengan kontroler ROV yang dipakai.
- **Pindah fitur.** Tab AquaClear, HydroDetect, dan SpatialSight tidak langsung memuat model; ketiganya membuka dialog 3.0 agar sistem melepas model yang sedang aktif lebih dulu. Tab Canvas langsung membuka Canvas karena Canvas tidak memuat model AI. Tombol LB/RB pada kontroler menggeser pilihan fitur tanpa melepas tangan dari kendali ROV.
- **Indikator kualitas citra.** Sistem menilai kekeruhan dari kontras frame. Pada kondisi sedang atau tinggi, kartu memberi saran: dekatkan ROV sekitar 0,5 m atau buka AquaClear. Saran ini sejalan dengan gerbang G2 pada task flow.
- **Posisi survei.** Kartu menampilkan segmen aktif sehingga pilot tahu bagian pipa yang sedang diukur dan berapa segmen lagi sampai PE+2.
- **Tandai temuan.** Menandai frame saat ini sebagai kandidat dan mengirimkannya ke antrian Review tanpa menghentikan video.
- **Selesai sesi.** Menghentikan rekaman dan membuka Penutupan sesi; diminta konfirmasi agar tidak tertekan tidak sengaja.

**Status dan kondisi gagal.**

- **REC / PAUSE:** rekaman berjalan atau dijeda.
- **LOST SIGNAL:** video membeku dengan banner merah, FREEZE dinonaktifkan agar frame lama tidak tersimpan sebagai bukti baru, dan sistem menunggu sinyal kembali.
- **GPU tinggi:** bila beban GPU melewati ambang, sistem menyarankan menutup fitur AI. Pada Optical sendiri beban tetap rendah karena tidak ada model yang berjalan.

**Aturan.** Video di layar ini tidak boleh diolah atau ditimpa overlay permanen. Semua overlay (penanda laser, kotak bantu) hanya tampilan dan tidak ikut tersimpan di rekaman asli. Setiap FREEZE dan Tandai temuan tercatat di log sesi dengan nama pengguna dan waktu.

## Window fitur Live Operation

### 3.0 – Dialog ganti window

**Tujuan.** Menegakkan aturan satu window fitur aktif dan mencegah konsol kelebihan beban GPU.

**Masuk dari / keluar ke.** Dari tab fitur di Optical (halaman 2 garis 1–3) atau tombol Ganti window di setiap fitur (garis 13, 17, 20). Keluar ke AquaClear (garis 8), HydroDetect (garis 9), SpatialSight (garis 10), atau kembali ke Optical lewat Batal (garis 11).

**Fitur dan cara kerja.** Dialog menampilkan fitur yang sedang aktif dan beban GPU saat ini, lalu tiga kartu pilihan beserta perkiraan beban: AquaClear rendah–sedang, HydroDetect tinggi, SpatialSight tinggi. Di bawahnya ada dua langkah proses: (1) melepas model lama, (2) memuat model baru. Setelah pengguna memilih, langkah 1 dijalankan lebih dulu, baru langkah 2. Bila pemuatan gagal, dialog menampilkan pesan dan kembali ke Optical. Video asli tetap berjalan selama proses sehingga pilot tidak kehilangan pandangan.

### 3.1 – AquaClear

**Tujuan.** Menjernihkan tampilan air keruh agar tepi pipa dan titik laser terlihat jelas, tanpa mengubah bukti asli.

**Masuk dari / keluar ke.** Dari dialog 3.0 atau dari Peringatan performa (garis 22). Keluar ke Mode Snapshot melalui "Kunci preset & FREEZE" (garis 12), dialog 3.0 (garis 13), atau Optical (garis 14).

**Fitur.** Tampilan berdampingan dengan penggeser: kiri video asli, kanan hasil AquaClear. Panel kanan berisi tiga preset (Inspection untuk kontras tepi pipa, Balanced untuk warna alami, Ringan untuk beban GPU kecil), penggeser koreksi warna, kontras, dan pengurangan partikel, serta sakelar tampilan berdampingan. Kartu gerbang G2 mengingatkan pertanyaan “tepi pipa dan titik laser jelas?” beserta tindakan bila belum.

**Aturan.** AquaClear hanya mengubah tampilan. FREEZE dari layar ini tetap menyimpan frame asli, sedangkan preset yang aktif dicatat di metadata agar reviewer tahu kondisi pandangan saat pengukuran.

### 3.2 – HydroDetect

**Tujuan.** Membantu menemukan kandidat temuan dengan segmentasi AI (model exp-5) sambil ROV bergerak.

**Masuk dari / keluar ke.** Dari dialog 3.0. Keluar ke Mode Snapshot (garis 15), Optical untuk konfirmasi di video asli (garis 16), dialog 3.0 (garis 17), Peringatan performa bila konsol melambat (garis 18), dan Review lewat Tandai ke Review.

**Fitur.** Overlay mask berwarna per kelas dengan label kelas dan nilai keyakinan (Leakage merah, Sandbag kuning, Pipe biru). Panel kanan menampilkan daftar kandidat frame ini dengan tautan “Cek di Optical”, penggeser ambang keyakinan, dan filter kelas (Leakage, Pipe, Sandbag, Spacer, Trunk/Root, Fish, Underwater trash). Indikator FPS dan GPU di kanan atas dapat diklik untuk membuka Peringatan performa.

**Aturan.** Hasil AI selalu berstatus kandidat sampai dikonfirmasi manusia di Review. Kelas yang dimatikan di filter tidak dihapus dari data, hanya disembunyikan dari tampilan.

### 3.3 – SpatialSight

**Tujuan.** Memberi gambaran dekat–jauh relatif untuk menemukan celah di bawah pipa dan memperkirakan lokasi G kiri dan G kanan sebelum pengukuran.

**Masuk dari / keluar ke.** Dari dialog 3.0. Keluar ke Mode Snapshot (garis 19), dialog 3.0 (garis 20), atau Optical.

**Fitur dan aturan.** Peta kedalaman berwarna dengan legenda dekat–jauh dan label tetap “Preview relatif, bukan ukuran”. Area gelap di bawah pipa ditandai sebagai indikasi bentang bebas. Panel kanan menjelaskan kegunaan, penggeser transparansi overlay, dan peringatan merah bahwa angka panjang tidak boleh diambil dari layar ini. Ukuran sah hanya melalui FREEZE, kalibrasi laser, dan pengukuran pada frame asli.

### 3.9 – Peringatan performa

**Tujuan.** Mencegah video tersendat dan FREEZE terlambat akibat beban GPU berlebih.

**Masuk dari / keluar ke.** Dari HydroDetect (garis 18) atau otomatis saat FPS turun di bawah ambang. Keluar ke Optical dengan fitur dimatikan (garis 21) atau ke AquaClear preset ringan (garis 22).

**Fitur dan aturan.** Dialog berbingkai kuning menampilkan penyebab dan tiga angka: FPS, beban GPU, dan memori GPU. Dua pilihan pemulihan ditampilkan sebagai tombol besar. Ambang FPS ditetapkan di Pengaturan. Setiap kejadian dicatat di log sesi untuk evaluasi Teknisi program.

## 3.4 – Canvas ukur dan anotasi

**Tujuan.** Canvas adalah ruang kerja untuk mengukur dan memberi tanda pada frame yang sudah dibekukan. Di sini pengguna menaruh node langsung di atas gambar: dua node untuk kalibrasi, dua node untuk panjang, tiga atau empat titik untuk luas, dan dua titik untuk anotasi. Hasil ukur langsung tampil sebagai garis atau bidang beserta nilainya, sehingga reviewer dapat melihat persis dari mana sebuah angka berasal.

**Pengguna.** Ahli pengukuran sebagai pengguna utama; Pilot drone dan Pemeriksa teknik untuk anotasi dan koreksi.

**Masuk dari / keluar ke.** Dari tab Canvas di Optical (halaman 2 garis 4), dari Gallery “Buka di Canvas” (garis 37), dan dari Review “Koreksi ukur di Canvas”. Keluar ke Review (garis 23), Simpan snapshot, atau Optical (garis 24).

**Tata letak.**

1. **Baris kepala:** tombol “← Optical”, label Canvas, label FROZEN dengan frame ID, dan kotak petunjuk langkah di kanan, misalnya “Kalibrasi: klik node 2 dari 2”.
2. **Toolbar kiri** dalam tiga kelompok bernomor sesuai urutan kerja: 1 Kalibrasi; 2 Ukur (Panjang dan Luas); 3 Anotasi. Di bawahnya tombol Undo dan Hapus.
3. **Bilah opsi kontekstual** di atas gambar. Isinya berubah menurut mode: kolom panjang referensi (cm) pada Kalibrasi, pilihan 3 titik atau 4 titik pada Luas, pilihan bentuk dan lima warna pada Anotasi.
4. **Area gambar** berbingkai oranye dengan kursor silang. Klik di mana pun pada gambar menaruh titik.
5. **Panel kanan:** kartu “Kalibrasi terakhir” (status, referensi, skala mm/px) dan kartu “Hasil ukur” yang mendaftar semua panjang dan luas, beserta catatan rumus.

**Cara kerja per mode.**

*Kalibrasi.* Pengguna mengisi panjang referensi antar dua titik laser dalam sentimeter, lalu mengklik node 1 dan node 2 tepat di pusat kedua titik laser. Sistem menghitung jarak piksel antar node dan menetapkan skala: skala (m/px) = panjang referensi (m) ÷ jarak piksel. Garis hijau putus-putus dengan label “ref xx cm” tampil di gambar, dan status berubah dari UNCALIBRATED menjadi VALID. Kalibrasi terakhir inilah yang dipakai semua ukuran berikutnya pada frame ini. Mengulang kalibrasi mengganti skala lama, dan ukuran yang sudah ada dihitung ulang dengan skala baru.

*Panjang.* Pengguna mengklik node 1 lalu node 2. Garis biru tampil dengan label “L1 = x,xx m” tepat di atas titik tengahnya. Panjang = jarak piksel × skala. Pengukuran berikutnya diberi nomor L2, L3, dan seterusnya. Mode ini menggantikan Distance; untuk lintasan berliku, panjang diukur sebagai beberapa ruas berurutan.

*Luas.* Pengguna memilih 3 titik atau 4 titik, lalu mengklik titik sudut berurutan mengelilingi bidang. Setelah titik terakhir, bidang kuning transparan muncul, setiap sisi diberi label panjangnya, dan label “A1 = x,xx m²” tampil di tengah bidang. Untuk 3 titik, luas dihitung dari tiga panjang sisi dengan rumus Heron: s = (a + b + c) ÷ 2 dan luas = √(s(s−a)(s−b)(s−c)). Untuk 4 titik, empat sisi saja belum cukup menentukan luas, sehingga sistem menarik diagonal dari titik 1 ke titik 3 (garis putus-putus), membagi bidang menjadi dua segitiga, menghitung masing-masing dengan rumus Heron, lalu menjumlahkannya. Cara ini mempertahankan prinsip “luas dari panjang sisi” dan membuat setiap angka dapat diperiksa ulang secara manual.

*Anotasi.* Pengguna memilih Panah, Garis, atau Tanda bulat dan salah satu dari lima warna (merah, kuning, biru, hijau, putih). Klik titik awal lalu titik akhir. Untuk panah, ujung panah digambar di titik akhir; untuk tanda bulat, titik pertama adalah pusat dan jarak ke titik kedua menjadi jari-jari. Anotasi tidak membutuhkan kalibrasi.

**Undo dan Hapus.** Undo membatalkan aksi terakhir (kalibrasi, ukur, atau anotasi). Hapus membersihkan semua lapisan pada frame ini dan juga dapat dibatalkan dengan Undo.

**Aturan dan validasi.**

- Panjang dan Luas tidak dapat dipakai sebelum kalibrasi; petunjuk menampilkan “Kalibrasi dulu sebelum mengukur” dan klik pada gambar diabaikan.
- Berganti mode membatalkan titik yang belum lengkap, sehingga tidak ada garis setengah jadi.
- Titik yang terlalu dekat tepi objek ditandai DEPTH\_EDGE\_RISK pada versi produksi, dan hasil yang terkena peringatan tidak boleh dipakai untuk Kalkulator span.
- Semua lapisan disimpan terpisah dari frame asli; frame asli tidak pernah diubah.
- “Simpan & kirim ke Review” menyimpan seluruh node, skala, dan hasil ke JSON snapshot lalu memasukkannya ke antrian Review.

**Catatan simulasi.** Pada mockup, nilai dihitung dari posisi klik pada gambar contoh dan panjang referensi bawaan 10 cm. Angka tersebut hanya memperagakan alur, bukan ukuran nyata.

## 3.5 – Mode Snapshot

**Tujuan.** Mode Snapshot mengubah satu frame video asli menjadi bukti ukur yang sah. Layar ini menggabungkan kalibrasi (3.5.1), pemeriksaan status kalibrasi (C2), pengukuran (3.5.2), dan pemeriksaan tepi objek (U2) dalam satu tempat. Hasilnya adalah angka panjang atau luas yang selalu disertai skala, ketidakpastian, dan metadata, sehingga dapat dipertanggungjawabkan di Kalkulator span, Review, dan Laporan.

**Pengguna.** Ahli pengukuran; Pilot drone menahan posisi ROV selama frame dibekukan.

**Masuk dari / keluar ke.** Dari FREEZE di Optical (halaman 2 garis 5), AquaClear (garis 12), HydroDetect (garis 15), SpatialSight (garis 19), dari Simpan snapshot “Ukur titik lain” (garis 33), dan dari Kalkulator span “Ukur ulang”. Keluar ke Simpan snapshot dan ke Optical melalui RESUME (garis 26).

**Tata letak.**

1. **Pita kepala oranye:** “← Optical”, label FROZEN, frame ID, timecode, preset AquaClear yang tercatat, segmen aktif, nomor freeze (1 dari 2), dan tombol RESUME dengan peringatan bahwa kalibrasi akan dihapus.
2. **Toolbar alat ukur** di kiri: Kalibrasi (K), Distance (D), Path (P), Area (A), Hapus titik, Undo (Ctrl+Z).
3. **Frame terkunci** berbingkai oranye tebal. Di atasnya tampil lingkaran hijau pada titik laser yang terdeteksi, garis ukur biru, dan label nilai.
4. **Kotak konfirmasi laser otomatis** di atas frame dengan tiga pilihan: Terima (Enter), Geser titik, atau Klik manual (cadangan).
5. **Panel kanan:** status kalibrasi tiga tingkat, cek kewajaran skala dari diameter pipa, slot multi-frame untuk segmen kritis, peringatan DEPTH\_EDGE\_RISK, metadata, dan tombol Simpan snapshot.

**Cara kerja langkah demi langkah.**

*Langkah 1 – Kalibrasi (alternatif A2 terpilih).* Begitu frame dibekukan, sistem mencari dua titik laser dan menandainya dengan lingkaran hijau. Sistem mengusulkan skala (mm/px) berdasarkan panjang referensi laser dari Pengaturan. Operator menekan Terima bila posisi tepat, Geser titik bila meleset sedikit, atau Klik manual bila deteksi gagal (alternatif A1 sebagai cadangan wajib). Kaca pembesar muncul saat titik digeser agar penempatan presisi.

*Langkah 2 – Gerbang C2.* Sistem menilai kalibrasi menjadi salah satu dari tiga status. UNCALIBRATED (merah): titik tidak ditemukan atau tidak masuk akal; tombol ukur nonaktif dan operator diminta mengulang (garis 28). ESTIMATE\_ONLY (kuning): skala ada tetapi kualitas titik meragukan; ukuran boleh diambil dengan label perkiraan. VALID (hijau): skala sah dan pengukuran dibuka (garis 29). Cek kewajaran membandingkan diameter pipa terukur dengan diameter nominal; selisih di atas ambang yang ditetapkan tim memicu peringatan.

*Langkah 3 – Ukur.* Distance memakai dua titik, Path memakai banyak titik mengikuti badan pipa, Area memakai poligon tertutup. Nilai langsung tampil di samping garis beserta ketidakpastian (±), dan titik dapat digeser dengan nilai diperbarui otomatis.

*Langkah 4 – Gerbang U2.* Bila titik ukur terlalu dekat tepi objek, banner DEPTH\_EDGE\_RISK muncul dan tombol Simpan nonaktif sampai titik digeser (garis 31). Bila bebas peringatan, hasil siap disimpan (garis 32).

*Langkah 5 – Multi-frame untuk segmen kritis (A5).* Untuk segmen yang menentukan L-total, sistem meminta dua freeze. Slot Freeze 1, Freeze 2, dan Selisih menunjukkan kemajuan; selisih harus ≤5 cm sesuai gerbang G4.

**Aturan.**

- Semua ukuran dihitung pada frame asli, bukan tampilan AquaClear atau overlay AI.
- Kalibrasi berlaku untuk satu frame saja. RESUME menghapus kalibrasi dan titik yang belum disimpan, setelah konfirmasi.
- Ukuran berstatus ESTIMATE\_ONLY tetap dapat disimpan, tetapi ditandai di Gallery dan Kalkulator span dan tidak boleh menjadi satu-satunya dasar keputusan kritis.
- Setiap aksi tercatat dengan nama pengguna dan waktu.

### 3.5.3 – Simpan snapshot

**Tujuan.** Mengonfirmasi bahwa bukti ukur tersimpan lengkap dan menentukan langkah berikutnya.

**Masuk dari / keluar ke.** Dari Mode Snapshot atau Canvas. Keluar ke Mode Snapshot “Ukur titik lain” (garis 33), Optical “Frame selesai · RESUME” (garis 34), atau Gallery (garis 35).

**Fitur dan aturan.** Dialog berlabel TERSIMPAN menampilkan thumbnail dengan garis ukur dan lima kartu ringkasan: ukuran beserta ketidakpastian, status kalibrasi dan sumbernya, pipa dan segmen, preset, serta nama berkas JPEG dan JSON. Kolom catatan opsional dipakai untuk kondisi lapangan, misalnya dasar sungai berlumpur. JPEG berisi frame beserta overlay ukur; JSON berisi titik, skala, ketidakpastian, dan metadata. Kedua berkas diberi nama dengan ID yang sama dan tidak dapat ditimpa; koreksi selalu membuat versi baru.

## Gallery dan Kalkulator span

### 5 – Gallery

**Tujuan.** Menjadi tempat semua snapshot misi dikumpulkan, disaring, diperiksa, dan diteruskan ke langkah berikutnya.

**Masuk dari / keluar ke.** Dari sidebar, Simpan snapshot (halaman 2 garis 35), Dashboard, dan Arsip “Buka paket”. Keluar ke Kalkulator span (garis 36), Canvas (garis 37), Review, dan Arsip lewat Ekspor paket.

**Tata letak dan fitur.** Baris kepala berisi judul, tombol oranye “Hitung span”, dan “Ekspor paket”. Empat filter tersedia: pipa, segmen, status kalibrasi, dan kelas temuan. Grid kartu snapshot menampilkan thumbnail, segmen, nomor freeze, dan status berwarna (VALID · lolos, selisih >5 cm, ESTIMATE\_ONLY). Panel detail di kanan menampilkan gambar lebih besar, ukuran, status kalibrasi, waktu dan operator, metadata JSON yang dapat dibuka, serta tombol Kirim ke Review dan Buka di Canvas.

**Aturan.** Snapshot tidak dapat dihapus dari Gallery oleh operator; penghapusan hanya lewat administrator dan tercatat. Snapshot dengan status selain VALID ditandai agar tidak terlewat saat menghitung span.

### 5.2 – Kalkulator span

**Tujuan.** Kalkulator span mengubah kumpulan ukuran per segmen menjadi satu keputusan teknik: apakah bentang bebas pipa melampaui batas kritis. Layar ini menjawab dua pertanyaan Pemeriksa teknik sekaligus: berapa panjang span, dan apakah angka itu sah. Desain terpilih adalah alternatif A2 (skema memanjang pipa) dengan tabel A1 di bawahnya.

**Pengguna.** Ahli pengukuran menyusun hasil; Pemeriksa teknik menilai.

**Masuk dari / keluar ke.** Dari Gallery (garis 36) dan Dashboard. Keluar ke Review bila cek silang lolos (garis 38), ke Mode Snapshot untuk ukur ulang segmen, atau ke Optical bila selisih melebihi batas (garis 39). Tombol “← Gallery” dan sidebar tersedia.

**Tata letak.**

1. **Kepala:** breadcrumb, judul pipa dan lokasi, serta tiga tab: Survei ini, Riwayat (aktif setelah survei kedua), dan Ekspor FEA (Fase 2).
2. **Skema memanjang pipa:** pipa digambar horizontal dari P0 sampai PE+2. Dasar sungai yang tergerus tampak sebagai cekungan di bawah pipa. Segmen S1–S6 tampil sebagai kotak berwarna di sepanjang span: hijau lolos, kuning perlu freeze ulang. Titik G kiri dan G kanan menandai ujung tumpuan. Garis ukur biru menunjukkan L-total, L-kiri, dan L-kanan; garis merah putus-putus menunjukkan batas kritis 9,65 m. Klik segmen membuka snapshot asalnya.
3. **Tabel rincian segmen:** segmen, freeze 1, freeze 2, selisih (≤5 cm), status kalibrasi, status, dan tautan snapshot. Baris yang gagal diberi latar kuning.
4. **Panel kanan:** cek silang, batang terhadap batas kritis, rekomendasi otomatis, serta tombol Kirim ke Review dan Ukur ulang segmen.

**Cara kerja perhitungan.**

1. Sistem mengambil semua snapshot pipa yang dipilih dan mengelompokkannya per segmen (sekitar 2 m per segmen sesuai skenario).
2. Setiap segmen harus memiliki dua freeze dengan selisih ≤5 cm (gerbang G4). Nilai segmen adalah rata-rata kedua freeze.
3. L-kiri dan L-kanan adalah jumlah segmen dari G kiri ke titik tengah dan dari titik tengah ke G kanan; L-total adalah jumlah keduanya.
4. Cek silang (gerbang G6): L-total dibandingkan dengan pengukuran tali, selisih harus ≤2%; uji batang 1 m sore harus dalam ±3%. Bila uji sore gagal, angka hari itu tidak sah dan tim kembali ke Fase K esok hari (halaman 3 garis 14).
5. Perbandingan batas (gerbang G7): L-total dibandingkan dengan batas kritis sesuai diameter pipa (16" 9,65 m; 8" 5,32 m) dan ditampilkan sebagai batang persentase.

**Rekomendasi otomatis.** Bila ada bagian yang mencapai atau melampaui batas: laporan, kajian FEA, dan perbaikan penopang (kotak merah). Bila di bawah batas: laporan dan survei ulang 6 bulan (kotak hijau). Rekomendasi ini bersifat usulan dan tetap diputuskan Pemeriksa teknik di Review.

**Aturan.**

- Tombol Kirim ke Review hanya aktif setelah semua segmen sah; selama ada segmen kuning, tombol menampilkan keterangan “aktif setelah S3 sah”.
- Segmen berstatus ESTIMATE\_ONLY ditandai dan memerlukan alasan bila tetap dipakai.
- Tab Riwayat membandingkan L-total antar survei untuk melihat gerusan yang bertambah, dan baru bermakna setelah minimal dua survei.
- Ekspor FEA dijadwalkan setelah format input disepakati dengan tim FEA.

## 4 – Review & Adjudikasi

**Tujuan.** Review adalah tempat manusia memutuskan setiap hasil AI dan setiap ukuran sebelum masuk laporan. Layar ini memastikan tidak ada kandidat AI yang menjadi temuan resmi tanpa diperiksa, dan tidak ada angka panjang atau luas yang dipakai tanpa kalibrasi yang sah. Desain terpilih menggabungkan alternatif A1 (tata letak antrian dan pratinjau), A4 (urutan berdasarkan risiko), A3 (dua pemeriksa untuk temuan kritis), dan A2 (shortcut keyboard untuk kelas risiko rendah).

**Pengguna.** Pemeriksa teknik sebagai pengambil keputusan; Ketua tim sebagai pemeriksa kedua untuk temuan kritis.

**Masuk dari / keluar ke.** Dari sidebar, Optical “Tandai temuan” (halaman 2 garis 6), HydroDetect, Canvas (garis 23), Gallery, Kalkulator span (garis 38), dan Dashboard. Keluar ke Laporan setelah keputusan (garis 40), Canvas untuk koreksi ukur, dan Mode Snapshot untuk ukur ulang. Sidebar dan tombol “← Kembali” tersedia untuk keluar kapan saja.

**Tata letak.**

1. **Kepala:** tombol kembali, breadcrumb “Dashboard › Review”, judul, dan tiga penghitung: Kritis, Sedang, Rendah.
2. **Antrian kiri:** kartu kandidat diurutkan otomatis berdasarkan risiko. Setiap kartu menampilkan tingkat risiko dan aturan pemeriksaan (misalnya “KRITIS · 2 pemeriksa”), sumber (HydroDetect, Kalkulator span, Canvas), nama temuan, dan ringkasan ukur (keyakinan, status kalibrasi, luas). Kartu terpilih berbingkai tebal.
3. **Tab lapisan verifikasi** di atas pratinjau: Overlay AI, Kalibrasi, Panjang, dan Luas segmen. Semua lapisan ditampilkan di atas frame asli yang sama.
4. **Pratinjau frame** besar di tengah.
5. **Panel Verifikasi ukuran** di kiri bawah dan **panel Keputusan** di kanan bawah.

**Cara kerja tab verifikasi.**

- **Overlay AI:** menampilkan mask dan label kelas beserta keyakinan, untuk menilai apakah AI menandai objek yang benar.
- **Kalibrasi:** menampilkan dua titik laser dan garis referensi yang dipakai, beserta panjang referensi dan status. Reviewer menilai apakah titik berada di pusat laser.
- **Panjang:** menampilkan garis ukur dan nilainya beserta ketidakpastian, untuk menilai apakah titik ujung berada di tepi objek yang benar.
- **Luas segmen:** menampilkan mask AI berwarna kuning dan poligon koreksi reviewer bergaris putih putus-putus. Perbedaan keduanya menunjukkan seberapa jauh AI meleset.

**Panel Verifikasi ukuran.** Panel ini merangkum tujuh butir: status kalibrasi beserta sumbernya, skala (mm/px), cek diameter nominal, panjang L beserta ketidakpastian, luas segmen dari mask AI, luas setelah koreksi beserta selisih persentase, dan status DEPTH\_EDGE\_RISK. Butir yang tidak lolos berwarna merah atau kuning agar langsung terlihat.

**Panel Keputusan.**

- **Konfirmasi temuan & ukuran:** temuan dan angka ukurnya diterima; kandidat pindah ke Laporan.
- **Tolak:** kandidat bukan temuan; data tetap disimpan sebagai contoh negatif untuk Analisis AI.
- **Ubah kelas:** kelas AI dikoreksi; data koreksi dikirim ke antrian pelatihan ulang.
- **Koreksi ukur di Canvas:** membuka Canvas dengan frame yang sama untuk memperbaiki node atau poligon.
- **Minta ukur ulang:** mengirim permintaan ke Ahli pengukuran dan membuka Mode Snapshot.
- **Alasan (wajib):** setiap keputusan harus disertai alasan, termasuk penilaian atas kalibrasi dan ukuran.
- **Jejak pemeriksa:** nama dan waktu pemeriksa pertama dan kedua tampil di bawah panel.

**Aturan prioritas antrian.** Urutan dari atas: (1) Leakage; (2) span yang mendekati atau melampaui batas kritis; (3) temuan dengan status ESTIMATE\_ONLY; (4) temuan sedang lain; (5) kelas risiko rendah seperti Fish dan Underwater trash. Di dalam satu tingkat, kandidat diurutkan menurut waktu.

**Aturan keputusan.**

- Temuan kritis (Leakage dan span ≥ batas) wajib disetujui dua pemeriksa yang berbeda. Status “1 dari 2 pemeriksa” tampil sampai pemeriksa kedua memutuskan.
- Shortcut Y (konfirmasi), N (tolak), E (ubah kelas) hanya aktif untuk kelas risiko rendah agar keputusan penting tidak diambil terburu-buru.
- Ukuran berstatus UNCALIBRATED tidak dapat dikonfirmasi; tombol Konfirmasi nonaktif sampai ukuran diperbaiki.
- Bila luas setelah koreksi berbeda jauh dari luas mask AI, keputusan tetap memakai luas koreksi, dan selisihnya dicatat untuk evaluasi model.
- Setiap keputusan tidak dapat dihapus; perubahan keputusan membuat catatan baru yang merujuk catatan lama.

## Laporan, PIMS/RBI, Analisis AI, Sustainability

### 6 – Laporan

**Tujuan.** Menyusun temuan terkonfirmasi menjadi laporan inspeksi resmi yang disetujui berjenjang.

**Masuk dari / keluar ke.** Dari Review (halaman 1 garis 19, halaman 2 garis 40), sidebar, dan Dashboard. Keluar ke PIMS/RBI melalui “Setujui & kirim ke PIMS” (halaman 1 garis 21) dan Penutupan sesi (halaman 2 garis 41).

**Tata letak dan fitur.** Kiri: pratinjau dokumen berlatar terang seperti kertas, berisi kepala laporan, ringkasan, tabel temuan terkonfirmasi (temuan, lokasi, bukti, pemeriksa), rekomendasi, dan hash paket bukti di kaki. Kanan: alur persetujuan tiga langkah (Draf, Diperiksa Pemeriksa teknik, Disetujui Ketua tim) dengan penanda selesai atau menunggu, serta tombol Setujui & kirim ke PIMS, Selesai · tutup sesi, dan Ekspor PDF.

**Aturan.** Isi laporan disusun otomatis dari temuan yang sudah diputuskan di Review; teks ringkasan dan rekomendasi dapat disunting. Setelah disetujui, laporan terkunci; revisi membuat versi baru dengan nomor revisi.

### 7 – PIMS / RBI

**Tujuan.** Memperbarui risiko segmen pipa berdasarkan temuan baru sesuai prosedur JOB Tomori.

**Masuk dari / keluar ke.** Dari Laporan (garis 21) dan sidebar. Keluar ke Arsip (garis 22).

**Fitur.** Matriks risiko 5×5 (PR-06-019) dengan penanda posisi sebelum survei (S) dan setelah temuan baru (B). Kartu PoF geohazard (PR-06-111): free span terhadap batas kritis, keberadaan mitigasi atau stabilisasi, dan kategori PoF. Kartu efektivitas inspeksi (PR-06-117): pilihan LoIE A–E dan interval inspeksi berikut (Low 3 tahun, Low to Moderate 2 tahun, Moderate ke atas 1 tahun). Tombol “Simpan risiko & arsipkan paket bukti”.

**Aturan.** Level LoIE dan interval diusulkan sistem tetapi ditetapkan Pemeriksa teknik. Warna matriks pada mockup masih ilustrasi dan harus diganti dengan warna posisi sesuai tabel PR-06-019.

### 8 – Analisis AI

**Tujuan.** Memantau kinerja model HydroDetect dan mengelola siklus perbaikan model.

**Masuk dari / keluar ke.** Dari sidebar (hanya Teknisi program). Keluar ke Pengaturan melalui “Rilis versi model” (garis 23).

**Fitur.** Tabel metrik per kelas untuk model aktif exp-5 (precision, recall, mAP50 mask, catatan), dengan pilihan pembanding versi kandidat. Kelas Leakage diberi catatan sebagai kelas kritis dengan data sedikit; Fish dan Underwater trash ditandai sebagai usulan penggabungan dalam revisi taksonomi 8→5 kelas. Kartu dataset (RCDV1 latih, validasi, label baru dari Review), riwayat versi, dan tombol Mulai pelatihan ulang.

**Aturan.** Metrik diisi dari hasil validasi resmi, bukan diketik manual. Model baru hanya aktif setelah dirilis dan tercatat di Pengaturan.

### 9 – Sustainability

**Tujuan.** Menampilkan manfaat keberlanjutan program inspeksi dari bulan ke bulan untuk manajemen dan penilaian CIP.

**Masuk dari / keluar ke.** Dari sidebar. Keluar ke Misi dengan mengklik kartu KPI (garis 24).

**Fitur.** Pilihan periode, empat kartu KPI (jam inspeksi, biaya dihemat, emisi dihindari dalam tCO₂e, temuan terkonfirmasi), dan grafik batang jam inspeksi per bulan. Grafik pada mockup hanya ilustrasi dan diisi dari data misi.

**Aturan.** Setiap KPI dapat ditelusuri ke misi asalnya. Rumus biaya dan emisi mengikuti workbook dashboard sustainability yang sudah disusun.

## Arsip, Pengaturan, Penutupan sesi

### 10 – Arsip

**Tujuan.** Menyimpan paket bukti setiap misi secara permanen dan membuktikan bahwa isinya tidak berubah sejak sesi ditutup.

**Masuk dari / keluar ke.** Dari PIMS/RBI (halaman 1 garis 22), Gallery “Ekspor paket”, Penutupan sesi, dan sidebar. Keluar ke Gallery melalui “Buka paket” (garis 25).

**Fitur.** Kolom pencarian (misi, pipa, tanggal) dan tabel paket: nama misi dan jenis survei, tanggal, isi paket (jumlah snapshot, laporan, log), potongan hash SHA-256, status integritas, dan tautan Buka paket. Catatan di bawah tabel menjelaskan cara pengecekan integritas.

**Cara kerja dan aturan.** Saat paket dibuka, sistem menghitung ulang hash seluruh berkas dan membandingkannya dengan hash yang tercatat saat penutupan sesi. Hasil sama berarti “Utuh” (hijau); hasil berbeda berarti “Perlu cek ulang” (kuning) dan dilaporkan ke Pengelola data. Paket di arsip hanya dapat dibaca; tidak ada tombol hapus atau ubah bagi pengguna biasa.

### 11 – Pengaturan

**Tujuan.** Menyimpan semua parameter yang memengaruhi ukuran dan keputusan di satu tempat yang terkontrol.

**Masuk dari / keluar ke.** Dari sidebar dan dari Analisis AI (garis 23). Keluar ke Dashboard melalui “Simpan perubahan” (garis 26).

**Fitur.** Empat kartu:

- **Alat referensi:** jarak dua titik laser (cm) dan panjang batang uji (1,00 m).
- **Ambang pemeriksaan:** uji batang ±3%, selisih dua freeze ≤5 cm, L-total vs tali ukur ≤2%, batas kritis 16"/8" 9,65 m / 5,32 m, dan ambang cek kewajaran diameter (ditetapkan tim).
- **Preset AquaClear dan kamera:** Inspection, Balanced, Ringan, serta model HydroDetect aktif.
- **Pengguna dan peran:** daftar pengguna, peran masing-masing, dan tombol Tambah pengguna.

**Aturan.** Hanya Teknisi program dan Ketua tim yang dapat mengubah Pengaturan. Setiap perubahan dicatat di audit log beserta nilai lama, nilai baru, nama, dan waktu. Perubahan ambang tidak mengubah hasil misi yang sudah ditutup.

### 12 – Penutupan sesi

**Tujuan.** Menutup sesi dengan aman dan menyegel paket bukti agar dapat diaudit.

**Masuk dari / keluar ke.** Dari Optical “Selesai sesi” (halaman 2 garis 7), Laporan (garis 41), dan menu Keluar di sidebar (halaman 1 garis 15). Keluar ke Login (garis 27) atau Arsip.

**Fitur dan cara kerja.** Empat kartu ringkasan (durasi, jumlah snapshot, ukuran tersimpan, temuan) dan empat langkah berurutan: (1) rekaman dihentikan, (2) paket bukti disusun, (3) hash dibuat, (4) unggah ke server dengan batang progres. Tombol Keluar dan Lihat di Arsip ada di bawah.

**Aturan.** Keluar hanya aktif setelah hash dibuat. Bila unggah gagal karena jaringan, paket tetap tersimpan di konsol dan diunggah otomatis saat jaringan tersedia; status ini terlihat di Arsip.

## Matriks keterlacakan dan hal terbuka

Setiap aturan ukur di mockup bersumber dari skenario atau prosedur, dan setiap gerbang terhubung ke garis flow map tertentu.

| Aturan | Nilai | Window yang menegakkan | Gerbang / garis flow map |
| --- | --- | --- | --- |
| Uji batang 1 m | ±3% | 2 Misi, 5.2 Kalkulator span | GK, G6 (hal. 3 garis 1–3, 14) |
| Kalibrasi frame | 2 titik laser, status 3 tingkat | 3.5 Snapshot, 3.4 Canvas | C2 (hal. 2 garis 27–29) |
| Titik dekat tepi objek | DEPTH\_EDGE\_RISK | 3.5 Snapshot, 3.4 Canvas, 4 Review | U2 (hal. 2 garis 30–32) |
| Dua freeze per segmen | selisih ≤5 cm | 3.5 Snapshot, 5.2 Kalkulator span | G4 (hal. 3 garis 8–11) |
| L-total vs tali ukur | ≤2% | 5.2 Kalkulator span | G6 (hal. 3 garis 12–15) |
| Batas kritis | 16" 9,65 m / 8" 5,32 m | 2 Misi, 5.2, 4 Review | G7 (hal. 3 garis 16–18) |
| Tindak lanjut | FEA atau survei ulang 6 bulan | 5.2, 6 Laporan | hal. 3 garis 17–18 |
| Matriks risiko | 5×5 | 7 PIMS/RBI | PR-06-019 |
| PoF geohazard | kategori PoF | 7 PIMS/RBI | PR-06-111 |
| LoIE dan interval | A–E; 3 / 2 / 1 tahun | 7 PIMS/RBI | PR-06-117 |
| Temuan kritis | 2 pemeriksa | 4 Review | hal. 2 garis 38, 40 |
| Satu fitur AI aktif | lepas model lewat 3.0 | 3, 3.0–3.3, 3.9 | hal. 2 garis 1–22 |

**Hal yang masih perlu ditetapkan tim**

- [ ] Ambang cek kewajaran skala dari diameter pipa (persen selisih yang memicu peringatan).
- [ ] Jumlah percobaan login sebelum dikunci dan lama penguncian.
- [ ] Ambang FPS dan beban GPU yang memicu Peringatan performa.
- [ ] Pemetaan tombol kontroler ROV untuk FREEZE dan ganti fitur (usulan: spasi/tombol A dan LB/RB).
- [ ] Warna posisi matriks 5×5 sesuai tabel PR-06-019.
- [ ] Format ekspor ke kajian FEA.
- [ ] Ambang ketidakpastian yang mengubah status VALID menjadi ESTIMATE\_ONLY.
