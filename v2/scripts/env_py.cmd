@echo off
rem Mengisi VENV_ABS dan ENV_PY. Pemanggil mengisi ROOT (folder v2, diakhiri \).
rem Urutan sama dengan deepinsight_engine/envloc.py. Tidak memakai Python sistem.
if not defined ROOT set "ROOT=%~dp0..\"
set "VENV_DIR=deepenv"
if defined DEEPINSIGHT_VENV (
  set "VENV_DIR=%DEEPINSIGHT_VENV%"
) else if exist "%ROOT%env.cfg" (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%ROOT%env.cfg") do (
    if /I "%%A"=="VENV_DIR" set "VENV_DIR=%%B"
  )
)
set "LEAD=%VENV_DIR:~1,1%"
set "HEAD=%VENV_DIR:~0,2%"
if "%LEAD%"==":" (
  set "VENV_ABS=%VENV_DIR%"
) else if "%HEAD%"=="\\" (
  set "VENV_ABS=%VENV_DIR%"
) else (
  set "VENV_ABS=%ROOT%%VENV_DIR%"
)
set "ENV_PY="
if exist "%VENV_ABS%\Scripts\python.exe" set "ENV_PY=%VENV_ABS%\Scripts\python.exe"
if not defined ENV_PY if exist "%VENV_ABS%\python.exe" set "ENV_PY=%VENV_ABS%\python.exe"
if not defined ENV_PY if exist "%VENV_ABS%\bin\python" set "ENV_PY=%VENV_ABS%\bin\python"
exit /b 0
