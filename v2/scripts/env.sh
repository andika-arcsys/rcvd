# Sumber bersama setup.sh dan start.sh. ROOT wajib folder v2.
# Urutan sama dengan deepinsight_engine/envloc.py.

load_venv_dir() {
  if [ -n "${DEEPINSIGHT_VENV:-}" ]; then
    VENV_DIR=$DEEPINSIGHT_VENV
  elif [ -f "$ROOT/env.cfg" ]; then
    VENV_DIR=$(sed -n 's/^VENV_DIR=//p' "$ROOT/env.cfg" | head -n 1 | tr -d '\r')
    VENV_DIR=${VENV_DIR:-deepenv}
  else
    VENV_DIR=deepenv
  fi
  VENV_DIR=${VENV_DIR%\"}
  VENV_DIR=${VENV_DIR#\"}
  case "$VENV_DIR" in
    /* | [A-Za-z]:* | [A-Za-z]:\\*) VENV_ABS=$VENV_DIR ;;
    *) VENV_ABS=$ROOT/$VENV_DIR ;;
  esac
}

find_env_python() {
  ENV_PY=""
  if [ -f "$VENV_ABS/Scripts/python.exe" ]; then
    ENV_PY=$VENV_ABS/Scripts/python.exe
  elif [ -f "$VENV_ABS/Scripts/python" ]; then
    ENV_PY=$VENV_ABS/Scripts/python
  elif [ -f "$VENV_ABS/python.exe" ]; then
    ENV_PY=$VENV_ABS/python.exe
  elif [ -f "$VENV_ABS/bin/python" ]; then
    ENV_PY=$VENV_ABS/bin/python
  fi
}
