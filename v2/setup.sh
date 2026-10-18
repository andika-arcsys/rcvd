#!/bin/sh
# Pakai ulang environment 3.12 (venv atau conda). Jangan menimpa versi lain.
set -e
cd "$(dirname "$0")"
ROOT=$(pwd)
# shellcheck disable=SC1091
. "$ROOT/scripts/env.sh"
load_venv_dir
find_env_python
mkdir -p "$ROOT/logs"
LOG=$ROOT/logs/setup.log
echo "=== setup ===" >> "$LOG"

if [ -n "$ENV_PY" ]; then
  ver=$("$ENV_PY" -c "import sys; print('%s.%s' % sys.version_info[:2])")
  if [ "$ver" != "3.12" ]; then
    echo "Environment ada tetapi bukan Python 3.12: $ENV_PY"
    echo "Tidak ditimpa. Periksa env.cfg."
    echo "Environment bukan Python 3.12, tidak ditimpa: $ENV_PY" >> "$LOG"
    exit 1
  fi
  echo "Memakai environment: $VENV_ABS"
  echo "Memakai environment: $VENV_ABS" >> "$LOG"
else
  if [ -d "$VENV_ABS" ]; then
    echo "Folder environment ada tetapi Python tidak ditemukan. Tidak ditimpa: $VENV_ABS"
    exit 1
  fi
  if command -v python3.12 >/dev/null 2>&1; then
    python3.12 -m venv "$VENV_ABS"
  else
    python3 -m venv "$VENV_ABS"
  fi
  find_env_python
  echo "Environment dibuat: $VENV_ABS"
  echo "Environment dibuat: $VENV_ABS" >> "$LOG"
fi

echo "Python: $ENV_PY" >> "$LOG"
"$ENV_PY" -m pip install -U pip >> "$LOG" 2>&1
if command -v nvidia-smi >/dev/null 2>&1; then
  echo "Requirements: requirements-gpu.txt" >> "$LOG"
  "$ENV_PY" -m pip install -r requirements-gpu.txt >> "$LOG" 2>&1
else
  echo "Requirements: requirements-cpu.txt" >> "$LOG"
  "$ENV_PY" -m pip install -r requirements-cpu.txt >> "$LOG" 2>&1
fi
if command -v pnpm >/dev/null 2>&1; then
  pnpm install
fi
echo "Selesai. Jalankan start.sh atau python start.py dari environment ini."
