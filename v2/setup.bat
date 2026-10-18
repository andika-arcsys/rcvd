@echo off
REM ==========================================================
REM DeepInsight - setup.bat (versi deepenv)
REM Memasang paket ke environment "deepenv" yang SUDAH ADA.
REM Tidak membuat environment baru, tidak memakai py launcher.
REM Jalankan dari folder v2:  setup.bat
REM ==========================================================
setlocal EnableDelayedExpansion

REM [1] Pindah ke folder tempat file ini berada (v2)
cd /d "%~dp0"

REM [2] Siapkan folder dan file log
if not exist logs mkdir logs
set "LOG=logs\setup.log"
echo.>> "%LOG%"
echo === setup %DATE% %TIME% ===>> "%LOG%"

REM [3] Pakai conda env "deepenv" yang sedang aktif.
REM     Contoh: conda activate deepenv  lalu  setup.bat
REM     Bila tidak aktif, cari folder v2\deepenv.
if /I "%CONDA_DEFAULT_ENV%"=="deepenv" if exist "%CONDA_PREFIX%\python.exe" (
  set "ENV_DIR=%CONDA_PREFIX%"
  set "ENV_PY=%CONDA_PREFIX%\python.exe"
  goto :found
)
set "ENV_DIR=%CD%\deepenv"
set "ENV_PY=%ENV_DIR%\Scripts\python.exe"
if not exist "%ENV_PY%" set "ENV_PY=%ENV_DIR%\python.exe"
if not exist "%ENV_PY%" (
  echo [GAGAL] Environment deepenv tidak ditemukan.
  echo         Dari folder v2 jalankan: conda activate deepenv
  echo         lalu setup.bat lagi.
  echo [GAGAL] deepenv tidak aktif dan tidak ada di %ENV_DIR%>> "%LOG%"
  exit /b 1
)
:found
echo [OK] Environment: %ENV_DIR%
echo Environment: %ENV_DIR%>> "%LOG%"
echo Python: %ENV_PY%>> "%LOG%"

REM [4] Pastikan Python di deepenv adalah 3.12
"%ENV_PY%" -c "import sys; raise SystemExit(0 if sys.version_info[:2]==(3, 12) else 1)"
if errorlevel 1 (
  echo [GAGAL] Python di deepenv bukan 3.12. Environment tidak diubah.
  "%ENV_PY%" --version
  echo [GAGAL] deepenv bukan Python 3.12>> "%LOG%"
  exit /b 1
)
echo [OK] Versi Python di deepenv:
"%ENV_PY%" --version
"%ENV_PY%" --version>> "%LOG%" 2>&1

REM [5] Perbarui pip di dalam deepenv
echo [..] Memperbarui pip ...
"%ENV_PY%" -m pip install --upgrade pip >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [GAGAL] Pembaruan pip gagal. Lihat %LOG%
  exit /b 1
)
echo [OK] pip diperbarui

REM [6] Pilih requirements: GPU bila nvidia-smi berhasil, selain itu CPU
nvidia-smi >nul 2>&1
if errorlevel 1 (
  set "REQ=requirements-cpu.txt"
  echo [i] GPU NVIDIA tidak terdeteksi - memakai requirements-cpu.txt
) else (
  set "REQ=requirements-gpu.txt"
  echo [i] GPU NVIDIA terdeteksi - memakai requirements-gpu.txt
)
echo Requirements: !REQ!>> "%LOG%"

REM [7] Pasang paket dari requirements ke deepenv
echo [..] Memasang paket dari !REQ! (bisa 10-30 menit) ...
"%ENV_PY%" -m pip install -r "!REQ!" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [GAGAL] Pemasangan paket gagal. Lihat %LOG%
  exit /b 1
)
echo [OK] Paket terpasang

REM [8] Periksa hasil pemasangan
"%ENV_PY%" -m pip check >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [PERINGATAN] Ada paket yang bentrok. Lihat %LOG%
) else (
  echo [OK] Tidak ada paket yang bentrok
)
"%ENV_PY%" -c "import fastapi, uvicorn, yaml, cv2, numpy, pydantic, argon2; print('[OK] Paket inti dapat diimpor')"
if errorlevel 1 (
  echo [GAGAL] Paket inti belum lengkap. Lihat %LOG%
  exit /b 1
)
"%ENV_PY%" -m pip freeze > logs\pip-freeze.txt

echo setup selesai>> "%LOG%"
echo.
echo Selesai. Jalankan aplikasi dengan:
echo    start.bat
echo atau:
echo    deepenv\Scripts\activate
echo    python start.py
exit /b 0
