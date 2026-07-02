"""
Sistem memory - menyimpan histori percakapan ke disk supaya Ferxvis "ingat"
percakapan sebelumnya walau aplikasi ditutup dan dibuka lagi.

Catatan: ini menyimpan PESAN PERCAKAPAN (teks chat), bukan menyimpan file/data
sensitif. File memory.json ada di folder root aplikasi, di luar workspace sandbox
(karena ini bukan "file kerja", tapi state aplikasi).
"""

import json
import os
from pathlib import Path

from config import MEMORY_FILE, MAX_HISTORY_MESSAGES


def load_memory() -> list:
    """
    Load histori percakapan dari disk.
    Mengembalikan list of messages, atau list kosong kalau belum ada/corrupt.
    """
    path = Path(MEMORY_FILE)
    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, OSError):
        # File corrupt atau tidak bisa dibaca - mulai dari kosong, jangan crash
        return []


def save_memory(messages: list) -> bool:
    """
    Simpan histori percakapan ke disk.
    Hanya menyimpan MAX_HISTORY_MESSAGES pesan terakhir (di luar system prompt)
    supaya file tidak membengkak tak terbatas.

    Mengembalikan True kalau berhasil, False kalau gagal (tidak melempar exception,
    supaya kegagalan menyimpan memory tidak menghentikan alur chat utama).
    """
    try:
        # Pisahkan system prompt (selalu index 0) dari pesan lainnya
        if messages and messages[0].get("role") == "system":
            system_msg = [messages[0]]
            rest = messages[1:]
        else:
            system_msg = []
            rest = messages

        trimmed = rest[-MAX_HISTORY_MESSAGES:] if len(rest) > MAX_HISTORY_MESSAGES else rest
        to_save = system_msg + trimmed

        path = Path(MEMORY_FILE)
        path.write_text(json.dumps(to_save, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def clear_memory() -> bool:
    """Hapus seluruh memory tersimpan (mulai percakapan dari nol)."""
    try:
        path = Path(MEMORY_FILE)
        if path.exists():
            path.unlink()
        return True
    except Exception:
        return False
