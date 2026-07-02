#!/bin/bash
# Launcher Ferxvis - jalankan ini bukan python3 main.py langsung

export FERXVIS_LLM_PROVIDER="groq"
export FERXVIS_GROQ_MODEL="llama-3.3-70b-versatile"

# Isi GROQ_API_KEY kamu di bawah ini (ganti teks dalam kutip)
export GROQ_API_KEY="${GROQ_API_KEY:-ISI_API_KEY_KAMU_DISINI}"

cd "$(dirname "$0")"
python3 main.py
