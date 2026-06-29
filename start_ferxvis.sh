#!/bin/bash
# Ferxvis v2.0 Launcher

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Cek ollama running (fallback offline)
if ! pgrep -x "ollama" > /dev/null 2>&1; then
    ollama serve > /tmp/ollama.log 2>&1 &
    sleep 2
fi

cd "$SCRIPT_DIR"
python3 main.py
