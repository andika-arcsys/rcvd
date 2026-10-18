#!/bin/sh
# Jalankan start.py dengan Python di env.cfg. Jangan jatuh ke Python sistem.
cd "$(dirname "$0")"
ROOT=$(pwd)
# shellcheck disable=SC1091
. "$ROOT/scripts/env.sh"
load_venv_dir
find_env_python
if [ -z "$ENV_PY" ]; then
  echo "Python environment tidak ditemukan."
  echo "Dicari:"
  echo "  $VENV_ABS/Scripts/python.exe"
  echo "  $VENV_ABS/python.exe"
  echo "  $VENV_ABS/bin/python"
  echo "Jalankan setup.sh atau periksa env.cfg. Python sistem tidak dipakai."
  exit 1
fi
exec "$ENV_PY" "$ROOT/start.py" "$@"
