"""
File tools - akses penuh ke seluruh home directory user.
"""

import os
import re
import shutil
from pathlib import Path

from config import WORKSPACE_DIR, HOME_DIR

# Pola placeholder gaya template yang TIDAK PERNAH boleh masuk ke isi file asli
# (mis. "{isi_email_terakhir}", "{nama_kontak}") — kalau ini lolos sampai sini,
# artinya tool/LLM sebelumnya gagal mengambil data asli tapi tetap mencoba
# menulis seolah-olah berhasil. Mencegah ini lebih murah daripada percaya
# pada hasil yang sudah ditulis ke disk.
_PLACEHOLDER_PATTERN = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")


def _looks_like_unresolved_placeholder(content: str) -> bool:
    """True kalau seluruh (atau hampir seluruh) konten cuma placeholder
    literal yang gak ke-substitusi, bukan isi/teks asli."""
    if not content:
        return False
    stripped = content.strip()
    # Heuristik: kalau setelah menghapus semua match placeholder, sisa teksnya
    # sangat pendek/kosong, berarti konten itu memang cuma placeholder polos.
    without_placeholders = _PLACEHOLDER_PATTERN.sub("", stripped)
    return bool(_PLACEHOLDER_PATTERN.search(stripped)) and len(without_placeholders) < 5


def _resolve_path(relative_path: str) -> Path:
    """Resolve path - support absolute dan relative (relatif ke home)."""
    rp = (relative_path or "").strip()
    if os.path.isabs(rp):
        target = Path(rp).resolve()
    else:
        target = (Path(HOME_DIR) / rp).resolve()
    return target


def _display_path(target: Path) -> str:
    try:
        return str(target.relative_to(HOME_DIR))
    except ValueError:
        return str(target)


def list_files(relative_path: str = "") -> str:
    target = _resolve_path(relative_path or HOME_DIR)
    if not target.exists():
        return f"Folder '{relative_path}' tidak ditemukan."
    if not target.is_dir():
        return f"'{relative_path}' adalah file, bukan folder."

    items = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    if not items:
        return f"Folder '{_display_path(target)}' kosong."

    lines = []
    for item in items:
        if item.name.startswith("."):
            continue
        kind = "📁" if item.is_dir() else "📄"
        size = ""
        if item.is_file():
            s = item.stat().st_size
            size = f" ({s//1024}KB)" if s > 1024 else f" ({s}B)"
        lines.append(f"{kind} {item.name}{size}")
    return "\n".join(lines) if lines else f"Folder '{_display_path(target)}' kosong (atau hanya hidden files)."


def create_folder(relative_path: str) -> str:
    target = _resolve_path(relative_path)
    if target.exists():
        return f"Folder '{_display_path(target)}' sudah ada."
    target.mkdir(parents=True, exist_ok=True)
    return f"Folder '{_display_path(target)}' berhasil dibuat."


def write_note(relative_path: str, content: str) -> str:
    if _looks_like_unresolved_placeholder(content):
        return (
            f"❌ GAGAL: konten yang akan ditulis ke '{relative_path}' cuma berisi "
            f"placeholder yang belum ke-isi ('{content.strip()}'), bukan teks asli. "
            "Tidak ditulis ke file. Kemungkinan langkah sebelumnya (mis. ambil data "
            "dari email/sumber lain) gagal — cek dan ambil data aslinya dulu."
        )
    target = _resolve_path(relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"File '{_display_path(target)}' berhasil disimpan."


def append_note(relative_path: str, content: str) -> str:
    if _looks_like_unresolved_placeholder(content):
        return (
            f"❌ GAGAL: konten yang akan ditambahkan ke '{relative_path}' cuma berisi "
            f"placeholder yang belum ke-isi ('{content.strip()}'), bukan teks asli. "
            "Tidak ditambahkan ke file. Kemungkinan langkah sebelumnya gagal — cek dan "
            "ambil data aslinya dulu."
        )
    target = _resolve_path(relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as f:
        if target.exists() and target.stat().st_size > 0:
            f.write("\n")
        f.write(content)
    return f"Teks berhasil ditambahkan ke '{_display_path(target)}'."


def read_file(relative_path: str) -> str:
    target = _resolve_path(relative_path)
    if not target.exists():
        return f"File '{relative_path}' tidak ditemukan."
    if not target.is_file():
        return f"'{relative_path}' adalah folder."
    try:
        return target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"File '{relative_path}' bukan file teks (kemungkinan binary)."


def move_file(source_relative_path: str, destination_relative_path: str) -> str:
    source = _resolve_path(source_relative_path)
    destination = _resolve_path(destination_relative_path)
    if not source.exists():
        return f"'{source_relative_path}' tidak ditemukan."
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.is_dir():
        destination = destination / source.name
    shutil.move(str(source), str(destination))
    return f"Berhasil dipindahkan ke '{_display_path(destination)}'."


def copy_file(source_relative_path: str, destination_relative_path: str) -> str:
    source = _resolve_path(source_relative_path)
    destination = _resolve_path(destination_relative_path)
    if not source.exists():
        return f"'{source_relative_path}' tidak ditemukan."
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(str(source), str(destination))
    else:
        shutil.copy2(str(source), str(destination))
    return f"Berhasil dicopy ke '{_display_path(destination)}'."


def delete_file(relative_path: str) -> str:
    target = _resolve_path(relative_path)
    if not target.exists():
        return f"'{relative_path}' tidak ditemukan."
    display = _display_path(target)
    if target.is_dir():
        shutil.rmtree(target)
        return f"Folder '{display}' dan seluruh isinya berhasil dihapus."
    else:
        target.unlink()
        return f"File '{display}' berhasil dihapus."


def rename_file(relative_path: str, new_name: str) -> str:
    target = _resolve_path(relative_path)
    if not target.exists():
        return f"'{relative_path}' tidak ditemukan."
    new_target = target.parent / new_name
    target.rename(new_target)
    return f"Berhasil diubah namanya menjadi '{new_name}'."


def search_files(query: str, search_path: str = "") -> str:
    """Cari file berdasarkan nama di dalam folder."""
    base = _resolve_path(search_path) if search_path else Path(HOME_DIR)
    results = []
    try:
        for p in base.rglob(f"*{query}*"):
            if not any(part.startswith(".") for part in p.parts):
                results.append(str(p))
            if len(results) >= 20:
                break
    except Exception:
        pass
    if not results:
        return f"Tidak ada file yang cocok dengan '{query}'."
    return "File ditemukan:\n" + "\n".join(results[:20])
