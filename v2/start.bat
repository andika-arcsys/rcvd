@echo off
REM ==========================================================
REM DeepInsight - start.bat (versi deepenv)
REM Menjalankan start.py memakai Python dari deepenv.
REM Argumen diteruskan, misalnya: start.bat --port 8080
REM ==========================================================
cd /d "%~dp0"

if /I "%CONDA_DEFAULT_ENV%"=="deepenv" if exist "%CONDA_PREFIX%\python.exe" (
  set "ENV_PY=%CONDA_PREFIX%\python.exe"
  goto :run
)
set "ENV_DIR=%CD%\deepenv"
set "ENV_PY=%ENV_DIR%\Scripts\python.exe"
if not exist "%ENV_PY%" set "ENV_PY=%ENV_DIR%\python.exe"
if not exist "%ENV_PY%" (
  echo [GAGAL] Environment deepenv tidak ditemukan.
  echo         Jalankan dulu: conda activate deepenv
  echo         lalu start.bat
  pause
  exit /b 1
)
:run

"%ENV_PY%" start.py %*
echo.
echo Aplikasi berhenti.
pause
