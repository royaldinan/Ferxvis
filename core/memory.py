"""
Memory & Chat History system untuk Ferxvis.
"""

import json
import os
from datetime import datetime
from pathlib import Path

from config import MEMORY_FILE, MAX_HISTORY_MESSAGES, CHAT_HISTORY_DIR, SAVED_CLIPBOARD_FILE


def load_memory() -> list:
    path = Path(MEMORY_FILE)
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_memory(messages: list) -> bool:
    try:
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
    try:
        path = Path(MEMORY_FILE)
        if path.exists():
            path.unlink()
        return True
    except Exception:
        return False


def save_chat_history(messages: list, title: str = None) -> str:
    """Simpan sesi chat ke file history dengan nama/timestamp."""
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in (title or "chat") if c.isalnum() or c in " _-")[:30].strip()
        filename = f"{ts}_{safe_title}.json"
        filepath = os.path.join(CHAT_HISTORY_DIR, filename)

        # Filter cuma user & assistant
        exportable = [m for m in messages if m.get("role") in ("user", "assistant") and m.get("content")]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "title": title or f"Chat {ts}",
                "saved_at": datetime.now().isoformat(),
                "messages": exportable
            }, f, ensure_ascii=False, indent=2)
        return filepath
    except Exception as e:
        return f"ERROR: {e}"


def list_chat_histories() -> list:
    """Return list of saved chat history files, sorted by newest first."""
    try:
        files = []
        for f in os.listdir(CHAT_HISTORY_DIR):
            if f.endswith(".json"):
                fp = os.path.join(CHAT_HISTORY_DIR, f)
                try:
                    with open(fp, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    files.append({
                        "filename": f,
                        "filepath": fp,
                        "title": data.get("title", f),
                        "saved_at": data.get("saved_at", ""),
                        "message_count": len(data.get("messages", [])),
                    })
                except Exception:
                    pass
        return sorted(files, key=lambda x: x["saved_at"], reverse=True)
    except Exception:
        return []


def load_chat_history(filepath: str) -> list:
    """Load chat history dari file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("messages", [])
    except Exception:
        return []


def delete_chat_history(filepath: str) -> bool:
    try:
        os.remove(filepath)
        return True
    except Exception:
        return False


# ── Saved Clipboard ──────────────────────────────────────────────
# Berbeda dari clipboard monitor biasa (yang otomatis terisi tiap copy dan
# hilang lagi kalau panel ditutup / app dibuka ulang) - ini daftar item
# yang SENGAJA disimpan user lewat tombol "Simpan", dan persist ke disk
# sama seperti save_chat_history, jadi tetap ada saat Ferxvis dibuka lagi.

def load_saved_clipboard() -> list:
    """Load daftar item clipboard yang sudah disimpan user, terbaru duluan."""
    path = Path(SAVED_CLIPBOARD_FILE)
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def add_saved_clipboard_item(text: str, label: str = None) -> bool:
    """Tambah satu item ke saved clipboard. Skip kalau teks sama persis sudah ada."""
    try:
        items = load_saved_clipboard()
        if any(i.get("text") == text for i in items):
            return False
        items.insert(0, {
            "text": text,
            "label": label or "",
            "saved_at": datetime.now().isoformat(),
        })
        path = Path(SAVED_CLIPBOARD_FILE)
        path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def delete_saved_clipboard_item(saved_at: str) -> bool:
    """Hapus satu item saved clipboard berdasarkan timestamp uniknya."""
    try:
        items = load_saved_clipboard()
        new_items = [i for i in items if i.get("saved_at") != saved_at]
        path = Path(SAVED_CLIPBOARD_FILE)
        path.write_text(json.dumps(new_items, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def clear_saved_clipboard() -> bool:
    """Hapus semua item saved clipboard."""
    try:
        path = Path(SAVED_CLIPBOARD_FILE)
        if path.exists():
            path.unlink()
        return True
    except Exception:
        return False
