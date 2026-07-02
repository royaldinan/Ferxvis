"""
Tools untuk operasi file & folder.

PENTING - SANDBOX SECURITY:
Semua fungsi di sini memaksa path yang diberikan untuk tetap berada di dalam
WORKSPACE_DIR (lihat config.py). Ini dilakukan dengan resolve_safe_path(),
yang akan menolak path apapun yang mencoba "keluar" dari workspace
(misal lewat "../../../Windows/System32" atau path absolut ke folder lain).

Jangan hapus / lewati pemanggilan resolve_safe_path() di fungsi manapun.
"""

import os
import shutil
from pathlib import Path

from config import WORKSPACE_DIR


class SandboxViolationError(Exception):
    """Dilempar saat ada upaya mengakses path di luar workspace."""
    pass


def resolve_safe_path(relative_path: str) -> Path:
    """
    Ubah path yang diminta (relatif terhadap workspace) menjadi path absolut yang aman.
    Menolak path yang mencoba keluar dari WORKSPACE_DIR.
    """
    relative_path = (relative_path or "").strip()

    # PENTING: Path absolut (mis. "/etc/passwd" atau "C:\Windows") harus ditolak total,
    # JANGAN digabung dengan workspace_root, karena pathlib akan menggantikan base path
    # sepenuhnya kalau bagian kedua adalah path absolut (Path("/a") / "/b" == Path("/b")).
    # Strip semua leading slash/backslash dan drive letter Windows (mis. "C:") supaya
    # path selalu diperlakukan sebagai relatif terhadap workspace.
    relative_path = relative_path.strip("/\\")
    if len(relative_path) >= 2 and relative_path[1] == ":":
        # Buang drive letter gaya Windows, contoh "C:\Windows" -> "Windows"
        relative_path = relative_path[2:].strip("/\\")

    workspace_root = Path(WORKSPACE_DIR).resolve()

    # Gabungkan dengan workspace root, lalu resolve untuk menormalkan ../ dsb
    candidate = (workspace_root / relative_path).resolve()

    # Cek: apakah candidate masih di dalam workspace_root?
    try:
        candidate.relative_to(workspace_root)
    except ValueError:
        raise SandboxViolationError(
            f"Akses ditolak: '{relative_path}' mengarah ke luar workspace yang diizinkan "
            f"({workspace_root}). Ferxvis hanya boleh bekerja di dalam workspace."
        )

    return candidate


def _display_path(target: Path) -> str:
    """Path relatif terhadap workspace, untuk ditampilkan di pesan ke user (akurat, bukan input mentah)."""
    workspace_root = Path(WORKSPACE_DIR).resolve()
    rel = target.relative_to(workspace_root)
    return str(rel) if str(rel) != "." else "(folder utama workspace)"


def list_files(relative_path: str = "") -> str:
    """List semua file & folder di dalam path (relatif terhadap workspace)."""
    try:
        target = resolve_safe_path(relative_path)
    except SandboxViolationError as e:
        return f"ERROR: {e}"

    if not target.exists():
        return f"Folder '{relative_path or '.'}' tidak ditemukan di workspace."

    if not target.is_dir():
        return f"'{relative_path}' adalah file, bukan folder."

    items = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    if not items:
        return f"Folder '{relative_path or '.'}' kosong."

    lines = []
    for item in items:
        kind = "📁" if item.is_dir() else "📄"
        lines.append(f"{kind} {item.name}")
    return "\n".join(lines)


def create_folder(relative_path: str) -> str:
    """Buat folder baru (termasuk parent folder kalau belum ada) di dalam workspace."""
    try:
        target = resolve_safe_path(relative_path)
    except SandboxViolationError as e:
        return f"ERROR: {e}"

    if target.exists():
        return f"Folder '{_display_path(target)}' sudah ada, tidak dibuat ulang."

    target.mkdir(parents=True, exist_ok=True)
    return f"Folder '{_display_path(target)}' berhasil dibuat."


def write_note(relative_path: str, content: str) -> str:
    """
    Buat atau timpa file teks (catatan) di dalam workspace.
    Kalau parent folder belum ada, akan dibuat otomatis.
    """
    try:
        target = resolve_safe_path(relative_path)
    except SandboxViolationError as e:
        return f"ERROR: {e}"

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Catatan berhasil disimpan di '{_display_path(target)}'."


def append_note(relative_path: str, content: str) -> str:
    """Tambahkan teks ke akhir file yang sudah ada (atau buat baru kalau belum ada)."""
    try:
        target = resolve_safe_path(relative_path)
    except SandboxViolationError as e:
        return f"ERROR: {e}"

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as f:
        if target.exists() and target.stat().st_size > 0:
            f.write("\n")
        f.write(content)
    return f"Teks berhasil ditambahkan ke '{_display_path(target)}'."


def read_file(relative_path: str) -> str:
    """Baca isi sebuah file teks di dalam workspace."""
    try:
        target = resolve_safe_path(relative_path)
    except SandboxViolationError as e:
        return f"ERROR: {e}"

    if not target.exists():
        return f"File '{relative_path}' tidak ditemukan."
    if not target.is_file():
        return f"'{relative_path}' adalah folder, bukan file."

    try:
        return target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"File '{relative_path}' bukan file teks biasa (kemungkinan biner)."


def move_file(source_relative_path: str, destination_relative_path: str) -> str:
    """Pindahkan file/folder dari satu lokasi ke lokasi lain, masih di dalam workspace."""
    try:
        source = resolve_safe_path(source_relative_path)
        destination = resolve_safe_path(destination_relative_path)
    except SandboxViolationError as e:
        return f"ERROR: {e}"

    if not source.exists():
        return f"'{source_relative_path}' tidak ditemukan."

    destination.parent.mkdir(parents=True, exist_ok=True)

    # Kalau destination adalah folder yang sudah ada, pindahkan ke dalamnya
    if destination.exists() and destination.is_dir():
        destination = destination / source.name

    shutil.move(str(source), str(destination))
    return f"Berhasil dipindahkan dari '{_display_path(source)}' ke '{_display_path(destination)}'."


def delete_file(relative_path: str) -> str:
    """Hapus file atau folder (beserta isinya) di dalam workspace."""
    try:
        target = resolve_safe_path(relative_path)
    except SandboxViolationError as e:
        return f"ERROR: {e}"

    if not target.exists():
        return f"'{relative_path}' tidak ditemukan, tidak ada yang dihapus."

    display = _display_path(target)
    if target.is_dir():
        shutil.rmtree(target)
        return f"Folder '{display}' dan seluruh isinya berhasil dihapus."
    else:
        target.unlink()
        return f"File '{display}' berhasil dihapus."
