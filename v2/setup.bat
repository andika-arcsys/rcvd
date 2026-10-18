@echo off
cd /d "%~dp0"
if not exist logs mkdir logs
set "LOG=logs\setup.log"
set "VENV_PY=%CD%\.venv\Scripts\python.exe"
echo === setup ===>> "%LOG%"

if exist "%VENV_PY%" goto :use

where py >nul 2>&1
if errorlevel 1 (
  echo Python launcher py tidak ada. Pasang Python 3.12.
  echo Python launcher py tidak ada. Pasang Python 3.12.>> "%LOG%"
  exit /b 1
)
py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info[:2]==(3, 12) else 1)"
if errorlevel 1 (
  echo Perlu Python 3.12.
  echo Perlu Python 3.12.>> "%LOG%"
  exit /b 1
)
echo Membuat environment: %CD%\.venv
py -3.12 -m venv .venv >> "%LOG%" 2>&1
if not exist "%VENV_PY%" (
  echo Gagal membuat .venv. Lihat %LOG%
  exit /b 1
)
echo Environment dibuat: %CD%\.venv>> "%LOG%"
goto :install

:use
echo Memakai environment: %CD%\.venv
echo Memakai environment: %CD%\.venv>> "%LOG%"

:install
"%VENV_PY%" -c "import sys; raise SystemExit(0 if sys.version_info[:2]==(3, 12) else 1)"
if errorlevel 1 (
  echo .venv ada tetapi bukan Python 3.12. Tidak ditimpa: %VENV_PY%
  echo .venv bukan Python 3.12, tidak ditimpa: %VENV_PY%>> "%LOG%"
  exit /b 1
)
echo Python: %VENV_PY%
echo Python: %VENV_PY%>> "%LOG%"
"%VENV_PY%" -c "import sys; print(sys.prefix)" >> "%LOG%" 2>&1
"%VENV_PY%" -m pip install -U pip >> "%LOG%" 2>&1
if errorlevel 1 (
  echo Pemasangan pip gagal. Lihat %LOG%
  exit /b 1
)
nvidia-smi >nul 2>&1
if errorlevel 1 (
  echo Requirements: requirements-cpu.txt
  echo Requirements: requirements-cpu.txt>> "%LOG%"
  "%VENV_PY%" -m pip install -r requirements-cpu.txt >> "%LOG%" 2>&1
) else (
  echo Requirements: requirements-gpu.txt
  echo Requirements: requirements-gpu.txt>> "%LOG%"
  "%VENV_PY%" -m pip install -r requirements-gpu.txt >> "%LOG%" 2>&1
)
if errorlevel 1 (
  echo Pemasangan paket gagal. Lihat %LOG%
  exit /b 1
)
where pnpm >nul 2>&1
if not errorlevel 1 call pnpm install
echo setup selesai>> "%LOG%"
call "%CD%\.venv\Scripts\activate.bat"
echo Environment aktif: %VIRTUAL_ENV%
echo Selesai. Bila prompt belum (.venv), jalankan perintah ini dengan call setup.bat
exit /b 0
