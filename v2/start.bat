@echo off
REM ==========================================================
REM DeepInsight - start.bat (versi deepenv)
REM Menjalankan start.py memakai Python dari deepenv.
REM Argumen diteruskan, misalnya: start.bat --port 8080
REM ==========================================================
cd /d "%~dp0"

set "ENV_DIR=%CD%\deepenv"
set "ENV_PY=%ENV_DIR%\Scripts\python.exe"
if not exist "%ENV_PY%" set "ENV_PY=%ENV_DIR%\python.exe"
if not exist "%ENV_PY%" (
  echo [GAGAL] Python deepenv tidak ditemukan di %ENV_DIR%
  echo         Jalankan setup.bat atau buat deepenv terlebih dahulu.
  pause
  exit /b 1
)

"%ENV_PY%" start.py %*
echo.
echo Aplikasi berhenti.
pause
