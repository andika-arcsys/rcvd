@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "ROOT=%~dp0"
call "%~dp0scripts\env_py.cmd"
if not defined ENV_PY (
  echo Python environment tidak ditemukan.
  echo Dicari:
  echo   %VENV_ABS%\Scripts\python.exe
  echo   %VENV_ABS%\python.exe
  echo Jalankan setup.bat atau periksa env.cfg. Python sistem tidak dipakai.
  exit /b 1
)
"%ENV_PY%" "%~dp0start.py" %*
exit /b %ERRORLEVEL%
