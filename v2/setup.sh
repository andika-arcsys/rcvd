#!/bin/sh
# Buat venv Python 3.12 dan pasang requirements sesuai GPU. Log: logs/setup.log
set -e
cd "$(dirname "$0")"
mkdir -p logs
LOG=logs/setup.log
{
  echo "=== setup $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  if command -v python3.12 >/dev/null 2>&1; then
    PY=python3.12
  else
    PY=python3
  fi
  "$PY" -c 'import sys; raise SystemExit(0 if sys.version_info[:2]==(3,12) else 1)'
  "$PY" -m venv .venv
  # shellcheck disable=SC1091
  . .venv/bin/activate
  python -m pip install -U pip
  if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    echo "GPU terdeteksi: requirements-gpu.txt"
    python -m pip install -r requirements-gpu.txt
  else
    echo "GPU tidak terdeteksi: requirements-cpu.txt"
    python -m pip install -r requirements-cpu.txt
  fi
  if command -v pnpm >/dev/null 2>&1; then
    pnpm install
  else
    echo "pnpm tidak ada. Pasang Node 20+ dan pnpm sebelum start.py membangun UI."
  fi
  echo "setup selesai"
} >>"$LOG" 2>&1
echo "Selesai. Lihat $LOG"
