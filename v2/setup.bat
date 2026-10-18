@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "ROOT=%~dp0"
if not exist logs mkdir logs
set "LOG=logs\setup.log"
echo === setup ===>> "%LOG%"
call "%~dp0scripts\env_py.cmd"

if defined ENV_PY goto :have
if exist "%VENV_ABS%\" (
  echo Folder environment ada tetapi Python tidak ditemukan. Tidak ditimpa: %VENV_ABS%
  echo Dicari: %VENV_ABS%\Scripts\python.exe dan %VENV_ABS%\python.exe
  echo Folder environment ada tetapi Python tidak ditemukan. Tidak ditimpa: %VENV_ABS%>> "%LOG%"
  exit /b 1
)
where py >nul 2>&1
if errorlevel 1 (
  echo Python launcher py tidak ada, dan environment belum ada: %VENV_ABS%
  echo Pasang Python 3.12, atau buat environment conda lalu isi env.cfg.
  exit /b 1
)
echo Membuat environment: %VENV_ABS%
py -3.12 -m venv "%VENV_ABS%" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo Gagal membuat environment. Lihat %LOG%
  exit /b 1
)
call "%~dp0scripts\env_py.cmd"
if not defined ENV_PY (
  echo Environment dibuat tetapi python.exe tidak ditemukan: %VENV_ABS%
  exit /b 1
)
echo Environment dibuat: %VENV_ABS%
echo Environment dibuat: %VENV_ABS%>> "%LOG%"
goto :install

:have
"%ENV_PY%" -c "import sys; raise SystemExit(0 if sys.version_info[:2]==(3, 12) else 1)"
if errorlevel 1 (
  echo Environment ada tetapi bukan Python 3.12: %ENV_PY%
  echo Tidak ditimpa. Periksa env.cfg.
  echo Environment bukan Python 3.12, tidak ditimpa: %ENV_PY%>> "%LOG%"
  exit /b 1
)
echo Memakai environment: %VENV_ABS%
echo Memakai environment: %VENV_ABS%>> "%LOG%"

:install
echo Python: %ENV_PY%>> "%LOG%"
"%ENV_PY%" -m pip install -U pip >> "%LOG%" 2>&1
if errorlevel 1 exit /b 1
nvidia-smi >nul 2>&1
if errorlevel 1 (
  echo Requirements: requirements-cpu.txt>> "%LOG%"
  "%ENV_PY%" -m pip install -r requirements-cpu.txt >> "%LOG%" 2>&1
) else (
  echo Requirements: requirements-gpu.txt>> "%LOG%"
  "%ENV_PY%" -m pip install -r requirements-gpu.txt >> "%LOG%" 2>&1
)
if errorlevel 1 (
  echo Pemasangan paket gagal. Lihat %LOG%
  exit /b 1
)
where pnpm >nul 2>&1
if not errorlevel 1 call pnpm install
echo Selesai. Jalankan start.bat
exit /b 0
