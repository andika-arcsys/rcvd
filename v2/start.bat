@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Jalankan setup.bat terlebih dahulu.
  exit /b 1
)
.venv\Scripts\python.exe start.py %*
