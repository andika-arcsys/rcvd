@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs
set LOG=logs\setup.log
echo === setup === >> "%LOG%"
where py >nul 2>&1
if errorlevel 1 (
  echo Python launcher py tidak ada. Pasang Python 3.12.>> "%LOG%"
  echo Python launcher py tidak ada. Pasang Python 3.12.
  exit /b 1
)
py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info[:2]==(3, 12) else 1)" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo Perlu Python 3.12.>> "%LOG%"
  echo Perlu Python 3.12.
  exit /b 1
)
py -3.12 -m venv .venv >> "%LOG%" 2>&1
call .venv\Scripts\activate.bat
python -m pip install -U pip >> "%LOG%" 2>&1
nvidia-smi >nul 2>&1
if errorlevel 1 (
  echo GPU tidak terdeteksi: requirements-cpu.txt>> "%LOG%"
  python -m pip install -r requirements-cpu.txt >> "%LOG%" 2>&1
) else (
  echo GPU terdeteksi: requirements-gpu.txt>> "%LOG%"
  python -m pip install -r requirements-gpu.txt >> "%LOG%" 2>&1
)
where pnpm >nul 2>&1
if errorlevel 1 (
  echo pnpm tidak ada. Pasang Node 20+ dan pnpm.>> "%LOG%"
) else (
  call pnpm install >> "%LOG%" 2>&1
)
echo setup selesai>> "%LOG%"
echo Selesai. Lihat %LOG%
