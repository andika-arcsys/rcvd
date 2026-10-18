# Panduan instalasi DeepInsight

Untuk orang yang memasang aplikasi di laptop Windows. DeepInsight 0.9.0-rc1 dibuka di browser, alamat `http://127.0.0.1:8000/`. Tidak ada file installer.

Semua perintah di panduan ini diketik di **Command Prompt**. Cara membukanya: tombol Windows, ketik `cmd`, Enter. Jendela itu bilah hitam dengan tulisan di akhirnya, disebut prompt.

Folder kerja hanya satu: `D:\DeepInsight\v2`. Environment hanya satu, namanya `deepenv`, diaktifkan dengan `conda activate deepenv`. Environment conda itu tidak harus berupa folder `v2\deepenv`. `setup.bat` memakai environment yang sedang aktif.

Bila langkah singkat di bab 4 selesai dan browser terbuka, bab lanjutan (CUDA, model, kalibrasi) tidak perlu dibaca untuk pemakaian pertama.

## 1. Batasan

| Yang dipakai | Di luar batas aplikasi ini |
| --- | --- |
| Jendela boleh Anaconda Prompt, setelah `conda deactivate` | Memasang paket selama prompt masih `(base)` |
| Folder `D:\DeepInsight\v2` | Environment di `C:\`, di folder Anaconda, atau di drive lain |
| `conda activate deepenv`, Python 3.12 | Memasang paket ke `(base)`, atau mengira `deepenv` harus berupa folder `v2\deepenv` |
| Python 3.12 di dalam `deepenv` | Python 3.11 atau 3.13, termasuk Python pada `(base)` |
| `setup.bat` hanya memasang paket ke `deepenv` yang sudah ada | Mengharapkan `setup.bat` membuat environment, atau memakai `py` launcher |
| Data misi di `%LOCALAPPDATA%\DeepInsight` | Menyimpan data misi di dalam `deepenv` |

Menghapus `deepenv` hanya menghapus Python dan paket DeepInsight. Data misi, foto, dan laporan tidak ikut terhapus. `setup.bat` tidak membuat folder itu kembali.

## 2. Kegunaan tiap nama

| Nama | Kegunaan |
| --- | --- |
| `deepenv` | Rumah Python DeepInsight. Sudah dibuat sebelum `setup.bat`. Python-nya 3.12, di `deepenv\Scripts\python.exe` (venv) atau `deepenv\python.exe` (conda). |
| `python -m venv deepenv` | Membuat rumah itu sekali, hanya bila `python --version` sudah `Python 3.12.x`. |
| `setup.bat` | Memasang paket ke `deepenv` yang sudah ada. Tidak membuat environment. Tidak memakai `py` launcher. |
| `deepenv\Scripts\activate` | Mengubah prompt menjadi `(deepenv) D:\DeepInsight\v2>`. Tidak menyalakan aplikasi. |
| `start.bat` | Menjalankan `start.py` dengan Python dari `deepenv`. Dipakai setiap hari. |
| Browser | Tempat memakai aplikasi, di `http://127.0.0.1:8000/`. Menutup browser tidak mematikan aplikasi. Tutup dulu jendela Command Prompt yang menjalankan `start.bat`. |

## 3. Prompt yang benar

Setelah aktivasi, baris tempat Anda mengetik harus diawali persis seperti ini:

```text
(deepenv) D:\DeepInsight\v2>
```

Tiga bagian itu punya arti tetap:

1. `(deepenv)` — environment DeepInsight sedang aktif.
2. `D:` — Anda di drive D.
3. `\DeepInsight\v2` — Anda di folder aplikasi.

Bila `(deepenv)` tidak ada, berhenti. Jangan menjalankan `pip`. Ulangi aktivasi di bab 4.

Cek singkat, masih di prompt yang sama:

```bat
where python
python -c "import sys; print(sys.prefix)"
```

Hasil yang benar:

- baris pertama `where python` adalah `D:\DeepInsight\v2\deepenv\Scripts\python.exe`, atau `D:\DeepInsight\v2\deepenv\python.exe` bila environment itu conda
- `sys.prefix` adalah `D:\DeepInsight\v2\deepenv`

## 4. Dari drive D: sampai aplikasi menyala

Mulai dari prompt yang sekarang ada di layar. Contoh yang sudah terjadi:

```text
(base) D:\>
```

`(base)` adalah environment Anaconda. Python di situ versi 3.13. DeepInsight tidak memakai Python itu. Paket aplikasi tidak dipasang selama prompt masih bertuliskan `(base)`.

`D:\DeepInsight` sudah ada. Jangan menjalankan `git clone` lagi. Pesan `destination path 'DeepInsight' already exists` berarti folder itu sudah terisi.

Folder `v2` belum ada karena cabang yang aktif masih `main`. `main` hanya berisi berkas awal, tanpa aplikasi. Itu sebab `cd v2` menjawab `The system cannot find the path specified`.

Kerjakan berurutan. Setiap blok selesai bila hasilnya sesuai kalimat di bawah perintah.

### 4.1 Masuk ke folder yang sudah ada, lalu ambil cabang aplikasi

```bat
cd /d D:\DeepInsight
git status
git branch
git fetch origin
git checkout cursor/panduan-environment-awam-ddf4
dir v2\setup.bat
```

Hasil yang benar:

- `git branch` semula menandai `main`
- setelah checkout, cabang aktif `cursor/panduan-environment-awam-ddf4`
- `dir v2\setup.bat` menampilkan berkas `setup.bat`, bukan `File Not Found`

| Bila muncul | Tindakan |
| --- | --- |
| `The system cannot find the path specified` pada `cd D:\DeepInsight` | Folder belum ada. Dari `D:\` jalankan `git clone https://github.com/andika-arcsys/rcvd.git DeepInsight`, lalu ulangi blok ini |
| `destination path already exists` | Folder sudah ada. Jangan clone. Lanjut `cd /d D:\DeepInsight` |
| `did not match any file` saat checkout | Ulangi `git fetch origin`, lalu checkout lagi |
| `Please commit your changes or stash them` | Di folder ini jalankan `git status`. Jangan dihapus. Kirim daftar berkasnya ke tim sebelum melanjutkan |

### 4.2 Keluar dari `(base)`, masuk ke folder v2

```bat
conda deactivate
cd /d D:\DeepInsight\v2
python --version
```

Hasil `python --version` harus `Python 3.12.x` sebelum environment dibuat. Bila yang tampil `3.13`, itu bukan Python DeepInsight. Pasang Python 3.12, buka jendela baru, ulangi `conda deactivate` dan `python --version`. `setup.bat` tidak memanggil `py` launcher.

Bila `conda` tidak dikenali, Anda sudah di Command Prompt biasa. Lanjut `cd` dan `python --version`.

### 4.3 Aktifkan `deepenv`, lalu pasang paket

```bat
cd /d D:\DeepInsight\v2
conda activate deepenv
python --version
setup.bat
```

Prompt harus `(deepenv)` dan `python --version` harus `Python 3.12.x`, seperti `Python 3.12.15`. `setup.bat` memakai environment conda yang sedang aktif itu. Ia tidak mencari folder `v2\deepenv`. Pemasangan pertama dapat berlangsung 10–30 menit. Selesai bila muncul `[OK] Environment:` dengan jalur conda, lalu `[OK] Paket inti dapat diimpor`.

Cek `logs\setup.log`. Di dalamnya ada `Environment: D:\DeepInsight\v2\deepenv` dan `setup selesai`.

### 4.5 Nyalakan aplikasi

```bat
cd /d D:\DeepInsight\v2
conda activate deepenv
start.bat
```

Prompt harus tetap `(deepenv)`. `start.bat` menjalankan `start.py` dengan Python environment itu. Biarkan jendela terbuka. Browser membuka `http://127.0.0.1:8000/`.

### 4.6 Bila Anda mengetik perintah sendiri

```bat
cd /d D:\DeepInsight\v2
deepenv\Scripts\activate
where python
python --version
python start.py
```

Prompt menjadi `(deepenv) D:\DeepInsight\v2>`. `where python` menunjuk ke `D:\DeepInsight\v2\deepenv\Scripts\python.exe`. Versi `Python 3.12.x`. Untuk conda, aktifkan environment itu dengan cara conda, dan `where python` menunjuk ke `D:\DeepInsight\v2\deepenv\python.exe`.

### 4.7 Setiap hari berikutnya

```bat
cd /d D:\DeepInsight\v2
start.bat
```

`deepenv` tidak dibuat ulang. `setup.bat` hanya diulang bila paket perlu dipasang lagi.

## 5. Environment rusak

Tutup dulu aplikasi. Hapus hanya folder `D:\DeepInsight\v2\deepenv`, lalu buat lagi dengan Python 3.12:

```bat
cd /d D:\DeepInsight\v2
rmdir /s /q deepenv
python --version
python -m venv deepenv
setup.bat
```

`python --version` harus 3.12 sebelum `python -m venv`. `setup.bat` sendiri tidak membuat `deepenv`.

## Lanjutan untuk teknisi

Bab 1 sampai 5 sudah cukup untuk memasang dan menyalakan aplikasi. Bagian di bawah menjelaskan perangkat, cek, dan gangguan. Jangan membuat environment lain saat membaca bagian ini.

## Cara kerjanya, setelah terpasang

1. `start.bat` memakai Python di dalam `deepenv` dan menjalankan `start.py`.
2. `start.py` menolak jalan bila Python bukan 3.12, atau bila paket inti belum terpasang.
3. Engine FastAPI dan uvicorn menyajikan antarmuka React dan API di port yang sama. Bawaan `127.0.0.1:8000`.
4. Konsol menulis mode GPU atau mode terbatas, lalu `Membuka browser http://127.0.0.1:8000/`.
5. Model AI dimuat ke GPU hanya ketika fiturnya dibuka (AquaClear, HydroDetect, SpatialSight). Satu model pada satu waktu. Model dilepas saat fitur ditutup. Bila VRAM tidak kembali ke garis dasar, proses pekerja dimatikan.

Dua mode:

- Mode GPU: `nvidia-smi` menampilkan GPU NVIDIA. `requirements-gpu.txt` terpasang. HydroDetect dan SpatialSight dapat dimuat.
- Mode terbatas: GPU tidak terbaca. Kode `GPU-001`. AquaClear berjalan di CPU (OpenCV). HydroDetect dan SpatialSight nonaktif. Pengukuran, snapshot, Gallery, Review, dan laporan tetap berjalan.

Alamat layar memakai tanda pagar, misalnya `http://127.0.0.1:8000/#/dashboard`. Jalur tanpa tanda pagar seperti `/dashboard` dan `/gallery` adalah API, bukan halaman.

## Kebutuhan laptop

Angka di tabel ini usulan awal. Angka yang diukur baru ada setelah `gpu_soak_test.py` di laptop inspeksi (D-01). Jangan menyalin nomor CUDA dari dokumen lain.

| Komponen | Minimum (usulan) | Disarankan (usulan) |
| --- | --- | --- |
| Sistem operasi | Windows 10/11 64-bit | Windows 11 64-bit |
| GPU | NVIDIA 6 GB VRAM, atau tanpa GPU (mode terbatas) | NVIDIA 8 GB VRAM |
| RAM | 16 GB | 32 GB |
| Penyimpanan | SSD 256 GB, sisa minimal 50 GB | SSD 512 GB |
| Layar | 1366×768 | 1920×1080 |

## Perangkat lunak yang dipakai aplikasi

Ini daftar yang benar-benar dipakai kode di `v2`, bukan daftar umum “software AI”.

| Perangkat | Wajib? | Dipakai untuk |
| --- | --- | --- |
| Python 3.12 64-bit, dengan `py` launcher dan pip | Wajib | Engine, pengukuran, OpenCV, API |
| Git for Windows | Wajib | Mengambil kode |
| Microsoft Visual C++ Redistributable x64 (2015–2022) | Wajib | DLL OpenCV dan ONNX di Windows |
| Driver NVIDIA | Wajib hanya untuk mode GPU | `nvidia-smi` dan CUDA |
| CUDA Toolkit dan cuDNN | Hanya bila ONNX Runtime tidak melihat GPU | Harus cocok dengan roda `onnxruntime-gpu` yang terpasang. Nomornya tidak dikunci di repo |
| Node.js 20 atau lebih baru | Hanya bila `apps\desktop\dist\index.html` belum ada | Membangun tampilan React |
| pnpm 10 (repo memakai 10.33.4 lewat Corepack) | Bersama Node.js | Memasang paket tampilan |
| Chrome atau Edge | Wajib | Membuka aplikasi |
| Microsoft C++ Build Tools | Hanya bila pip meminta “Microsoft Visual C++ 14.0 or greater” | Mengompilasi paket yang tidak punya roda |
| Notepad++ atau VS Code | Disarankan | Menyunting `config\*.yaml` |

Paket Python yang dipasang `requirements-cpu.txt` (dari `services/engine/pyproject.toml`):

- fastapi, uvicorn, websockets, pydantic, pyyaml, psutil, numpy, opencv-python-headless, argon2-cffi

`requirements-gpu.txt` memasang daftar yang sama, ditambah `nvidia-ml-py` dan `onnxruntime-gpu`.

`start.py` memeriksa impor ini sebelum layanan jalan: `fastapi`, `uvicorn`, `yaml`, `cv2`, `numpy`, `pydantic`, `argon2`.

PyTorch dan TensorFlow tidak ada di requirements. `ModuleNotFoundError` untuk keduanya adalah keadaan normal. Bila suatu saat terpasang di environment yang sama, aplikasi mengaktifkan memory growth TensorFlow. Runtime produksi model tetap ONNX Runtime.

Yang tidak dipakai: Rust, Tauri, Electron, dan pemasang NSIS.

## Memasang perangkat lunak

Pasang berurutan. Setelah setiap pemasangan, tutup Command Prompt lalu buka lagi, supaya PATH yang baru terbaca.

| No | Perangkat lunak | Sumber | Pilihan saat memasang | Cek |
| --- | --- | --- | --- | --- |
| 1 | Python 3.12 64-bit | python.org, Windows installer (64-bit) versi 3.12.x | Centang Add python.exe to PATH. Customize installation: pip, py launcher, dan for all users. Di akhir, Disable path length limit bila tombol itu muncul | `py -3.12 --version` menampilkan `Python 3.12.x` |
| 2 | Git for Windows | git-scm.com | Pada Adjusting your PATH pilih Git from the command line and also from 3rd-party software | `git --version` |
| 3 | Driver NVIDIA | nvidia.com, seri GPU laptop itu | Saat memperbarui driver lama: Custom, Clean installation | `nvidia-smi` menampilkan tabel GPU |
| 4 | Visual C++ Redistributable x64 | learn.microsoft.com, “Latest supported Visual C++ Redistributable”, berkas `vc_redist.x64.exe` | Tidak ada pilihan. Restart bila diminta | Settings, Apps, “Microsoft Visual C++ 2015-2022 Redistributable (x64)” |
| 5 | CUDA dan cuDNN | developer.nvidia.com | Hanya bila langkah cek ONNX di bawah tidak menampilkan `CUDAExecutionProvider`. Versi mengikuti tabel kompatibilitas ONNX Runtime untuk roda yang terpasang | `nvcc --version` setelah toolkit dipasang. Catat angkanya. Jangan menyalin nomor dari dokumen lain |
| 6 | Node.js LTS | nodejs.org | Biarkan pilihan bawaan. Centang “Automatically install the necessary tools” tidak diperlukan | `node --version` menampilkan v20 atau lebih baru |
| 7 | pnpm lewat Corepack | Ikut Node.js | Di cmd Administrator: `corepack enable` | `pnpm --version` |
| 8 | Chrome atau Edge | google.com/chrome, atau Edge bawaan Windows | — | `chrome://version` atau `edge://version` |
| 9 | C++ Build Tools | visualstudio.microsoft.com, Build Tools | Hanya bila pip meminta Visual C++ 14.0. Pilih beban kerja Desktop development with C++ | Ulangi pemasangan paket |
| 10 | Notepad++ atau VS Code | notepad-plus-plus.org atau code.visualstudio.com | — | Untuk menyunting YAML |

### Pengaturan Windows yang disarankan

Long paths, cmd sebagai Administrator:

```bat
reg add HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f
```

Hasil yang benar: `The operation completed successfully.`

Mode daya: colok charger dan pilih Best performance. Di NVIDIA Control Panel, Manage 3D settings, Global, pilih High-performance NVIDIA processor.

Antivirus: bila pemasangan paket gagal `Access is denied` atau sangat lambat, kecualikan folder `D:\DeepInsight`.

## Environment Python

Rincian bab 1 sampai 5. Environment tetap satu: `D:\DeepInsight\v2\deepenv`. Bagian ini tidak meminta environment kedua.

Jendela resmi adalah Command Prompt. Dua baris lain di tabel aktivasi hanya dipakai bila jendela yang terbuka kebetulan PowerShell atau Git Bash. Prompt yang sah tetap diawali `(deepenv)` dan folder tetap `D:\DeepInsight\v2`.

### Belum ada environment: buat

```bat
cd /d D:\DeepInsight\v2
python -m venv deepenv
dir deepenv\Scripts
```

Perintah pertama tidak menampilkan apa pun bila berhasil. `dir` harus menampilkan `python.exe`, `pip.exe`, `activate.bat`, `Activate.ps1`, dan `deactivate.bat`.

| Bila muncul | Artinya | Tindakan |
| --- | --- | --- |
| `Error: [WinError 5] Access is denied` | Folder terkunci atau tidak punya izin tulis | Cmd sebagai Administrator, atau pindahkan proyek ke `D:\` |
| Folder `deepenv` sudah ada dan rusak | Sisa pemasangan lama | `rmdir /s /q deepenv`, lalu buat lagi |

### Aktifkan, setiap jendela cmd baru

| Jendela | Perintah |
| --- | --- |
| Command Prompt | `deepenv\Scripts\activate` |
| PowerShell | `deepenv\Scripts\Activate.ps1` |
| Git Bash | `source deepenv/Scripts/activate` |

Tanda aktif: awal baris menjadi `(deepenv) D:\DeepInsight\v2>`.

Di PowerShell, bila muncul `running scripts is disabled on this system`:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Jawab `Y`, lalu ulangi aktivasi.

### Cek environment yang benar

```bat
python --version
where python
python -c "import sys; print(sys.prefix)"
```

Hasil yang benar:

- `Python 3.12.x`
- baris pertama `where python` adalah `D:\DeepInsight\v2\deepenv\Scripts\python.exe`
- `sys.prefix` menunjuk ke `D:\DeepInsight\v2\deepenv`

Bila mengarah ke `C:\Users\...\Python312`, environment belum aktif. Ulangi `activate`.

### Cek perangkat lunak di dalam environment

Jalankan ini setelah venv aktif. Catat keluarannya bila melapor ke tim pengembang.

```bat
python --version
python -m pip --version
python -c "import sys; print(sys.version); print(sys.prefix)"
where python
where git
git --version
nvidia-smi
node --version
pnpm --version
python -m pip check
python -c "import fastapi, uvicorn, yaml, cv2, numpy, pydantic, argon2; print('Paket inti OK', cv2.__version__)"
python -m pip list
python -m pip freeze > logs\pip-freeze.txt
```

Arti hasil:

| Cek | Hasil yang benar | Bila gagal |
| --- | --- | --- |
| `python --version` | 3.12.x dari `deepenv` | Aktifkan venv, atau buat ulang dengan `py -3.12` |
| `pip --version` | pip dari `D:\DeepInsight\v2\deepenv` dan python 3.12 | `python -m pip install --upgrade pip` |
| `git --version` | `git version 2.x` | Pasang Git, buka cmd baru |
| `nvidia-smi` | Tabel nama GPU, Driver Version, CUDA Version, memori | Tanpa GPU NVIDIA: lanjut mode terbatas. `nvidia-smi` tidak dikenali berarti driver belum ada |
| `node` dan `pnpm` | v20+ dan nomor pnpm | Hanya wajib bila `dist\index.html` belum ada |
| impor paket inti | `Paket inti OK` dan versi OpenCV 4.x | Ulangi pemasangan requirements |
| `pip check` | `No broken requirements found.` | Baca nama paket yang bentrok, ulangi install |

Laptop GPU, tambahan:

```bat
python -c "import onnxruntime as ort; print(ort.__version__); print(ort.get_available_providers())"
python -m pip list | findstr onnxruntime
```

Hasil yang benar: paketnya `onnxruntime-gpu`, dan daftar provider memuat `CUDAExecutionProvider` selain `CPUExecutionProvider`. `TensorrtExecutionProvider` boleh ada, tidak wajib.

| Bila muncul | Tindakan |
| --- | --- |
| Hanya `CPUExecutionProvider` | `pip list` harus menunjukkan `onnxruntime-gpu`, bukan `onnxruntime`. Bila nama sudah benar, cocokkan CUDA/cuDNN dengan tabel kompatibilitas roda itu. Catat versi driver, `onnxruntime-gpu`, CUDA, dan cuDNN |
| `ModuleNotFoundError: cv2` | Install requirements belum tuntas. Lihat `logs\pip-install.log` |
| `DLL load failed` | Pasang Visual C++ Redistributable x64, buka cmd baru, aktifkan venv, ulangi impor |
| `ModuleNotFoundError: torch` atau `tensorflow` | Normal. Keduanya tidak dipasang oleh requirements |

Keluar dari environment: `deactivate`. Awalan `(deepenv)` hilang.

Membuat ulang environment yang rusak:

```bat
deactivate
cd /d D:\DeepInsight\v2
rmdir /s /q deepenv
python -m venv deepenv
deepenv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements-gpu.txt
```

Ganti berkas terakhir dengan `requirements-cpu.txt` bila laptop tidak punya GPU NVIDIA.

## Instalasi manual, langkah demi langkah

Ini pemecahan bab 4 bila `setup.bat` berhenti atau Anda perlu melihat tiap hasil. Bila bab 4 sudah menyalakan browser, lewati bagian ini. Tetap di `D:\DeepInsight\v2` dan di environment `deepenv`. Pakai `python -m pip`, setelah prompt `(deepenv)`, agar paket masuk ke environment itu. Catatan otomatis `setup.bat` ada di `logs\setup.log`.

### Bagian A — cek prasyarat

Langkah 1, Python 3.12:

```bat
py -0p
py -3.12 --version
```

Hasil yang benar memuat `-V:3.12` dan jalur `python.exe`, lalu `Python 3.12.x`.

| Bila muncul | Tindakan |
| --- | --- |
| `'py' is not recognized` | Pasang Python 3.12 64-bit. Centang Add python.exe to PATH dan py launcher |
| `No suitable Python runtime found` | Yang ada bukan 3.12. Pasang 3.12. Versi 3.11 dan 3.13 tidak dipakai |
| Baris `-32` | Hapus Python 32-bit. Pasang 64-bit |

Langkah 2, Git:

```bat
git --version
```

Hasil yang benar: `git version 2.x.x.windows.x`. Bila tidak dikenali, pasang Git for Windows dan buka cmd baru.

Langkah 3, GPU:

```bat
nvidia-smi
```

Catat nama GPU, Driver Version, CUDA Version, dan memori. Angka itu dikirim saat melapor.

| Bila muncul | Tindakan |
| --- | --- |
| `'nvidia-smi' is not recognized` | Driver belum ada, atau laptop tanpa GPU NVIDIA. Aplikasi tetap jalan mode terbatas |
| `NVIDIA-SMI has failed` | Pasang ulang driver. Di NVIDIA Control Panel pilih High performance |

Langkah 4, ambil kode:

```bat
cd /d D:\
git clone https://github.com/andika-arcsys/rcvd.git DeepInsight
cd DeepInsight
git branch -a
git log -1 --oneline
cd v2
dir
```

Hasil yang benar: `Cloning into 'DeepInsight'...`, `Receiving objects: 100%`, satu baris `git log`, dan `dir` menampilkan `setup.bat`, `start.bat`, `start.py`, `requirements-gpu.txt`, `requirements-cpu.txt`, serta folder `config`, `scripts`, `services`, `apps`.

| Bila muncul | Tindakan |
| --- | --- |
| `Repository not found` atau minta login | Repo privat. Login GitHub saat diminta, atau pakai GitHub Desktop |
| Berkas di `v2` tidak lengkap | Cabang yang terambil belum berisi kode ini. Checkout cabang atau tag yang diberi tim, lalu ulangi `dir` |

Tag `v0.9.0-rc1` belum dibuat. Setelah tag ada, dari folder `DeepInsight` (bukan `v2`):

```bat
git fetch --tags
git checkout v0.9.0-rc1
cd v2
```

### Bagian B — environment dan paket

Semua perintah berikut dari `D:\DeepInsight\v2`.

Langkah 5, buat venv bila belum ada. Lewati bila `deepenv\Scripts\python.exe` sudah ada dan langkah 6 lolos.

```bat
python -m venv deepenv
dir deepenv\Scripts
```

Langkah 6, aktifkan dan cek `where python` seperti bagian Environment di atas.

Langkah 7, perbarui pip:

```bat
python -m pip install --upgrade pip
python -m pip --version
```

Hasil yang benar: `Successfully installed pip-...` atau `Requirement already satisfied`, lalu pip dari `deepenv` dengan python 3.12.

Langkah 8, pasang paket. Lihat dulu isinya:

```bat
type requirements-gpu.txt
type requirements-cpu.txt
mkdir logs
```

Pilih satu, sesuai langkah 3:

```bat
REM Laptop dengan GPU NVIDIA, nvidia-smi berhasil:
python -m pip install -r requirements-gpu.txt > logs\pip-install.log 2>&1

REM Laptop tanpa GPU NVIDIA:
python -m pip install -r requirements-cpu.txt > logs\pip-install.log 2>&1
```

Selama proses, log berisi `Collecting`, `Downloading`, `Installing collected packages`, dan diakhiri `Successfully installed`. Pasang pertama bisa 10–30 menit. Paket GPU berukuran ratusan MB.

```bat
type logs\pip-install.log | findstr /i "error successfully"
```

| Bila muncul | Tindakan |
| --- | --- |
| `No matching distribution` | Python bukan 3.12, atau roda tidak ada untuk Windows. Ulangi langkah 6 |
| `Microsoft Visual C++ 14.0 or greater is required` | Pasang C++ Build Tools, ulangi langkah 8 |
| `ReadTimeoutError` atau `ProxyError` | Ulangi. Di kantor yang memakai proxy: tambahkan `--proxy` dan `--timeout 120` pada perintah pip |
| `path too long` | Aktifkan Long Paths, ulangi |
| `WinError 5` | Tutup Python lain dan antivirus yang mengunci `deepenv`, ulangi |

Langkah 9, periksa pemasangan dengan perintah cek di bagian Environment. Laptop GPU harus melihat `CUDAExecutionProvider`.

### Bagian C — tampilan, model, dan config

Langkah 10, cek antarmuka sudah dibangun:

```bat
dir apps\desktop\dist\index.html
```

Bila berkas ada, lanjut. Bila `File Not Found`, `start.py` akan membangunnya, dan itu membutuhkan Node serta pnpm:

```bat
node --version
corepack enable
pnpm --version
```

`corepack enable` dijalankan sekali di cmd Administrator. Bila `node` tidak dikenali, pasang Node.js LTS, buka cmd baru, aktifkan venv lagi.

Langkah 11, folder model di luar repo:

```bat
mkdir D:\DeepInsight-models\hydrodetect\exp5
mkdir D:\DeepInsight-models\spatialsight
```

Salin berkas dari tim, lalu:

```bat
dir /s /b D:\DeepInsight-models
```

Hasil yang benar:

```text
D:\DeepInsight-models\hydrodetect\exp5\classes.json
D:\DeepInsight-models\hydrodetect\exp5\metadata.json
D:\DeepInsight-models\hydrodetect\exp5\model.onnx
D:\DeepInsight-models\spatialsight\model.onnx
```

Berkas `.onnx` dan `.pt` tidak ada di Git. Laptop GPU dapat membuka berkas HydroDetect:

```bat
python -c "import onnxruntime as ort; s=ort.InferenceSession(r'D:\DeepInsight-models\hydrodetect\exp5\model.onnx', providers=['CUDAExecutionProvider','CPUExecutionProvider']); print('Provider:', s.get_providers()); print('Input:', [(i.name, i.shape) for i in s.get_inputs()])"
```

Provider pertama yang diharapkan pada laptop GPU adalah `CUDAExecutionProvider`. `NO_SUCHFILE` atau `InvalidProtobuf` berarti berkas salah atau rusak saat disalin. Bentuk input mengikuti model yang diberikan tim. Jangan mengarang ukurannya bila perintah itu belum dijalankan.

Di laptop tanpa GPU, lewati perintah ONNX itu. HydroDetect akan ditolak aplikasi dengan `MDL-003`. Itu benar untuk mode terbatas.

Langkah 12, cek laser dan RMS. Nilai ini sudah diisi di repo:

```bat
findstr /i "ref_cm rms_good_px rms_max_px min_baseline_px valid_max_rel estimate_max_rel" config\thresholds.yaml
```

Hasil yang benar memuat:

- `ref_cm: 10` — dua titik laser berjarak 10 cm (SUMBER tim)
- `rms_good_px: 0.5` dan `rms_max_px: 1.0` — USULAN, praktik umum OpenCV
- `min_baseline_px: 150`
- `valid_max_rel: 0.03` dan `estimate_max_rel: 0.10`

Kunci di berkas adalah `valid_max_rel` dan `estimate_max_rel`, bukan `valid_pct`. Bila jarak laser di ROV yang dipakai bukan 10 cm, ubah hanya `ref_cm` dengan editor teks, lalu catat di audit lewat Pengaturan bila nilai itu diubah dari layar.

```bat
type config\video.yaml
type config\pipelines.yaml
```

`video.yaml` dengan sumber kosong berarti kamera ROV tidak dibuka saat aplikasi mulai. Aplikasi tetap dapat diuji. `pipelines.yaml` berisi pipa fixture `contoh`, bukan data lapangan.

### Bagian D — menjalankan dan memverifikasi

Langkah 13, dari venv yang aktif:

```bat
python start.py
```

Klik dua kali `start.bat` melakukan hal yang sama, memakai `deepenv\Scripts\python.exe`. Bila `deepenv` belum ada, `start.bat` berhenti dan menyuruh menjalankan `setup.bat`.

Urutan yang harus terlihat:

1. Tidak ada kalimat `Perlu Python 3.12` dan tidak ada `Paket belum lengkap`.
2. Satu baris mode: `Mode GPU: model dimuat saat fitur dibuka, satu pekerja.` atau `Mode terbatas: GPU tidak terbaca (GPU-001). AquaClear di CPU.`
3. Bila `dist` belum ada: pembangunan UI lewat pnpm. Itu bisa beberapa menit.
4. `Membuka browser http://127.0.0.1:8000/`.

Biarkan jendela ini terbuka. Uvicorn di sini tidak mencetak log akses (`log_config` dimatikan). Tidak adanya baris `Uvicorn running` bukan tanda gagal, selama `/health` menjawab.

| Bila muncul | Tindakan |
| --- | --- |
| `[GAGAL] Python di deepenv bukan 3.12` | Jangan lanjut. Buat ulang `deepenv` dengan Python 3.12. `setup.bat` tidak menimpa environment itu |
| `Paket belum lengkap` | Ulangi langkah 8–9. Nama paket yang hilang tertulis di pesan |
| Mode terbatas padahal ONNX melihat CUDA | Pemeriksaan mode memakai `nvidia-ml-py` (`nvidia-smi` / NVML), bukan provider ONNX. Laporkan kedua keluaran ke tim |
| `address already in use` atau port 8000 dipakai | Tutup konsol DeepInsight yang lama, atau `python start.py --port 8080` |
| Build UI gagal | Langkah 10 |

Langkah 14, buka cmd kedua. Venv tidak wajib untuk curl:

```bat
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/diagnostics
```

`/health` berisi `"status":"ok"` dan `session_id` berbentuk `SES-YYYYMMDD-HHMM`. `/diagnostics` berisi `app_version` `0.9.0-rc1`, `python` `3.12.x`, `model.state` `optical` saat baru mulai, `workers` 0, dan GPU. `gpu.error_code` `GPU-001` berarti mode terbatas. Tidak adanya kode error GPU berarti GPU terbaca.

Langkah 15, di browser:

1. `http://127.0.0.1:8000/` menampilkan Splash dan cek sistem. Tanpa GPU, tombol “Lanjut mode terbatas” yang dipakai.
2. Login memakai akun uji lokal di `docs/DATA_NEEDED.md`. Itu bukan personel lapangan. Akun administrator tidak dibuat otomatis saat instalasi.
3. Pilih peran Ketua tim, lalu “Lanjut ke Dashboard”.
4. Buka `http://127.0.0.1:8000/#/pengaturan`. Isi folder model `D:\DeepInsight-models` dan simpan. Tombolnya “Simpan folder model”.
5. Tekan F12, tab Console. Pindah layar lewat menu. Tidak boleh ada error merah.
6. Di Live Operation, AquaClear dapat dibuka di CPU. HydroDetect pada laptop GPU berpindah ke siap bila berkas model benar. Pada laptop tanpa GPU, HydroDetect ditolak `MDL-003`.

Langkah 16, hentikan. Tutup sesi lewat menu Keluar. Di konsol pertama tekan Ctrl+C. Pada laptop GPU, `nvidia-smi` setelah berhenti harus mendekati pemakaian memori pada langkah 3, karena tidak ada model yang masih dimuat.

### Titik periksa

| Langkah | Tanda berhasil |
| --- | --- |
| 1 | Python 3.12.x |
| 3 | Tabel `nvidia-smi`, atau sengaja mode terbatas |
| 4 | `setup.bat`, `start.py`, dan `requirements-*.txt` ada di `v2` |
| 6 | Prompt `(deepenv)` dan `where python` menunjuk ke `deepenv` |
| 8 | `Successfully installed` |
| 9 | `No broken requirements found.` Pada GPU: `CUDAExecutionProvider` |
| 11 | Empat berkas model ada. Pada GPU, sesi ONNX terbuka |
| 12 | `ref_cm: 10`, `rms_good_px: 0.5`, `rms_max_px: 1.0` |
| 13 | `Membuka browser http://127.0.0.1:8000/` |
| 14 | `/health` ok, `/diagnostics` versi `0.9.0-rc1` |
| 15 | Splash, login, Pengaturan, folder model tersimpan |
| 16 | Konsol berhenti dengan Ctrl+C. VRAM GPU kembali mendekati angka awal |

Setelah langkah ini berhasil sekali, pemakaian harian: buka cmd di `D:\DeepInsight\v2`, `deepenv\Scripts\activate`, `python start.py`. Atau klik dua kali `start.bat`.

## Konfigurasi

Nilai ambang ada di `config\`. Jangan menulis angka ambang di kode.

### Laser

```yaml
laser:
  ref_cm: 10
calibration:
  min_baseline_px: 150
  valid_max_rel: 0.03
  estimate_max_rel: 0.10
  camera_file_required_for_valid: true
```

Setelah FREEZE, skala = 0,10 m dibagi jarak piksel dua titik laser. Dua titik harus minimal 150 piksel agar petunjuk “dekatkan ROV” tidak muncul. Status VALID juga membutuhkan file kalibrasi kamera. Tanpa file itu, pengukuran laser tetap jalan dan status maksimal ESTIMATE_ONLY. Ukur ulang jarak 10 cm secara berkala dengan jangka sorong.

Contoh yang dikunci uji: 10 cm pada jarak 200 piksel menghasilkan skala 0,0005 m/px.

### Kamera dan RMS

| RMS | Tindakan |
| --- | --- |
| ≤ 0,5 px | Diterima. Berkas ditulis |
| di atas 0,5 px sampai 1,0 px | Diterima dengan peringatan. Berkas tetap ditulis |
| di atas 1,0 px | Ditolak. Berkas tidak ditulis. Ulangi foto |

`--squares 9x6` adalah jumlah sudut dalam, kolom kali baris, bukan jumlah kotak. `--square-mm` adalah sisi satu kotak dalam milimeter. Ganti keduanya agar cocok dengan papan yang dipakai. Dari `v2`, venv boleh tidak aktif karena jalur Python ditulis lengkap:

```bat
deepenv\Scripts\python scripts\calibrate_camera.py --images D:\kalibrasi\foto --squares 9x6 --square-mm 25 --camera-id rov01
```

Hasilnya `config\cameras\rov01.yaml`. Untuk ukur di bawah air, foto papan catur sebaiknya diambil di dalam air atau kolam, karena refraksi mengubah jalur cahaya. Rinciannya ada di `docs\CAMERA_CALIBRATION.md`.

### Berkas lain

| Berkas | Isi | Bila kosong |
| --- | --- | --- |
| `config\pipelines.yaml` | Daftar pipa | Fixture `contoh` tetap ada. Itu bukan data lapangan |
| `config\video.yaml` | USB, capture card, atau RTSP | Aplikasi tidak membuka perangkat saat mulai |
| `config\risk.yaml` | PR-06-019, PR-06-111, PR-06-117 | Layar PIMS berkata data belum diisi |
| `config\sustainability.yaml` | Rumus biaya dan emisi | Jam, biaya, dan emisi tampil tanda hubung |

Folder model dipilih di Pengaturan setelah aplikasi jalan.

## Menjalankan sehari-hari

1. Klik dua kali `start.bat`, atau dari cmd yang venv-nya aktif: `python start.py`.
2. Browser terbuka ke `http://127.0.0.1:8000/`. Bila tidak, salin alamat itu ke Chrome atau Edge.
3. Biarkan jendela konsol terbuka. Jendela itu adalah layanan web-nya.
4. Pakai satu tab browser.

| Perintah | Kegunaan |
| --- | --- |
| `start.bat --port 8080` | Port lain bila 8000 sudah dipakai |
| `start.bat --lan` | Perangkat lain di jaringan yang sama membuka `http://<IP-laptop>:8000/`. Wajib sudah ada akun PIN di `config\users.yaml`. Tanpa PIN, aplikasi menolak jalan |

Cek kapan saja:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/diagnostics`

Menghentikan: menu Keluar, lalu tutup konsol atau Ctrl+C.

## Penggunaan pertama

1. Splash. Tanpa GPU, pilih “Lanjut mode terbatas”.
2. Login dengan akun di `docs\DATA_NEEDED.md`.
3. Pilih peran dan “Lanjut ke Dashboard”.
4. Misi. Diameter 16 inci memakai batas 9,65 m. Diameter 8 inci memakai batas 5,32 m.
5. Pre-check. Uji batang 1 m: FREEZE, dua titik laser 10 cm, ukur dua ujung batang, hasil dalam ±3%. Setelah pre-check lolos, mulai misi.
6. Optical. Satu fitur AI pada satu waktu.
7. FREEZE dengan Spasi. Status VALID atau ESTIMATE_ONLY. Simpan. Dua freeze per segmen, selisih paling besar 5 cm.
8. Gallery dan kalkulator span. Tali ukur paling besar 2%. Uji batang sore ±3%.
9. Review, laporan, PIMS, arsip.
10. Penutupan menyusun paket dan hash SHA-256.

Alur layar yang lebih pendek ada di `docs\USER_GUIDE.md`.

## Memperbarui

```bat
cd /d D:\DeepInsight
git fetch --tags
git checkout <tag-baru>
cd v2
call deepenv\Scripts\activate.bat
python -m pip install -r requirements-gpu.txt
call setup.bat
```

Pakai `requirements-cpu.txt` bila laptop tanpa GPU. `setup.bat` boleh dijalankan ulang. Data misi di `%LOCALAPPDATA%\DeepInsight` tidak dihapus.

Uji GPU di laptop inspeksi, sekali dan setiap ganti driver:

```bat
deepenv\Scripts\python scripts\gpu_soak_test.py
deepenv\Scripts\python scripts\eval_hydrodetect.py
```

Kirim keluaran lengkap, kode keluar, `nvidia-smi`, `logs\pip-freeze.txt`, dan versi driver, `onnxruntime-gpu`, CUDA, serta cuDNN. Di mesin tanpa GPU, soak test berhenti kode 2. Itu bukan kelulusan.

## Masalah umum

| Gejala | Langkah |
| --- | --- |
| `FileNotFoundError` pada `pnpm` saat `start.bat` | Tampilan belum dibangun. `pnpm` di Windows bernama `pnpm.cmd`. Pasang Node.js 20, `corepack enable`, lalu dari `v2`: `pnpm install` dan `pnpm --filter @deepinsight/desktop build`. Program lama di folder `web` tidak memakai langkah ini |
| Prompt diawali `(base)` dan `python --version` 3.13 | Itu Anaconda. `conda deactivate`. Aplikasi memakai Python 3.12 di `deepenv` |
| `cd v2` tidak menemukan folder | Masih di cabang `main`. `git fetch origin` lalu `git checkout cursor/panduan-environment-awam-ddf4` |
| Prompt tidak diawali `(deepenv)` saat memasang paket | Berhenti. `cd /d D:\DeepInsight\v2` lalu `deepenv\Scripts\activate`. Jangan memasang paket |
| `python` tidak dikenali | Pasang ulang Python 3.12, centang Add to PATH, buka cmd baru |
| `where python` bukan `deepenv` | `deepenv\Scripts\activate` |
| Mode terbatas padahal ada GPU | `nvidia-smi`, perbarui driver, `python -m pip install -r requirements-gpu.txt` di venv yang aktif |
| Browser tidak terbuka | Buka `http://127.0.0.1:8000/` manual |
| Port 8000 sudah dipakai | Tutup konsol lama, atau `start.bat --port 8080` |
| HydroDetect `MDL-003` | Tidak ada GPU, atau folder model di Pengaturan salah. Lihat `/diagnostics` |
| Status selalu ESTIMATE_ONLY | Belum ada `config\cameras\<id>.yaml`. Pengukuran laser 10 cm tetap jalan |
| Status UNCALIBRATED | Titik laser lebih dekat dari 150 piksel, atau tidak terdeteksi |
| Video tidak muncul | `config\video.yaml` masih kosong, atau alamat sumber salah |
| Pesan berkode | Catat kode dan `session_id` dari `/health`. Lihat `docs\ERROR_CODES.md` dan `docs\TROUBLESHOOTING.md` |

## Lokasi berkas

| Lokasi | Isi |
| --- | --- |
| `v2\deepenv\` | Python dan paket aplikasi. Boleh dihapus dan dibuat ulang |
| `v2\logs\setup.log` | Catatan `setup.bat` / `setup.sh` |
| `v2\logs\pip-install.log` dan `pip-freeze.txt` | Dibuat oleh perintah di panduan ini, untuk laporan |
| `v2\config\` | Ambang dan pengaturan |
| `%LOCALAPPDATA%\DeepInsight` | Sesi, snapshot PNG dan JSON, log JSON sesi, cache, paket bukti |
| Folder model di Pengaturan | Bobot `.onnx`, di luar repo |

Log sesi tidak berada di `v2\logs\`. Log sesi berada di bawah folder data, pada `sessions\<SES-id>\logs`. Saat melapor, sertakan kode error, ID sesi dari `/health`, `logs\setup.log`, dan `logs\pip-freeze.txt`.

## Linux

Perintah yang sama, dari folder `v2`, bila environment belum ada:

```bash
cd /jalur/ke/rcvd/v2
python3.12 --version
python3.12 -m venv deepenv
. deepenv/bin/activate
python --version
python -c "import sys; print(sys.prefix)"
python -m pip install --upgrade pip
python -m pip install -r requirements-cpu.txt
```

Bila `nvidia-smi` berhasil, ganti berkas terakhir dengan `requirements-gpu.txt`. `./setup.sh` melakukan pembuatan venv, aktivasi, dan pilihan requirements itu, lalu menulis `logs/setup.log`.

Cek paket:

```bash
python -m pip check
python -c "import fastapi, uvicorn, yaml, cv2, numpy, pydantic, argon2; print('Paket inti OK', cv2.__version__)"
```

Menjalankan:

```bash
python start.py
```

Browser yang sama: `http://127.0.0.1:8000/`. `--port` dan `--lan` berlaku seperti di Windows.
