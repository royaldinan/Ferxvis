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


# ── Current directory (di dalam workspace) ──────────────────────────────
# State in-memory: posisi "folder kerja saat ini" milik Ferxvis, mirip
# konsep `cd` di terminal. Semua relative_path yang TIDAK diawali "/" akan
# dihitung relatif terhadap _current_dir, bukan langsung dari WORKSPACE_DIR.
# _current_dir sendiri selalu berupa path absolut yang sudah divalidasi ada
# di dalam WORKSPACE_DIR, jadi tidak bisa dipakai untuk kabur dari sandbox.
_current_dir: Path = Path(WORKSPACE_DIR).resolve()


def get_current_dir() -> Path:
    return _current_dir


def get_current_dir_display() -> str:
    """Current dir relatif terhadap workspace, untuk ditampilkan ke user."""
    return _display_path(_current_dir)


def resolve_safe_path(relative_path: str, base: "Path | None" = None) -> Path:
    """
    Ubah path yang diminta menjadi path absolut yang aman.
    Menolak path yang mencoba keluar dari WORKSPACE_DIR.

    - base: folder acuan untuk path relatif. Default-nya _current_dir
      (folder kerja Ferxvis saat ini), BUKAN selalu WORKSPACE_DIR.
      Ini membuat change_directory() benar-benar berefek pada tool-tool lain.
    - Path yang diawali "/" atau "\\" dianggap absolut TERHADAP WORKSPACE_DIR
      (bukan terhadap current_dir), supaya user/LLM masih bisa "lompat balik"
      ke folder utama workspace kapan saja dengan relative_path="/Documents"
      misalnya, tanpa perlu tahu current_dir sedang di mana.
    """
    relative_path = (relative_path or "").strip()
    workspace_root = Path(WORKSPACE_DIR).resolve()
    base = (base or _current_dir).resolve()

    is_explicitly_from_workspace_root = relative_path.startswith(("/", "\\"))

    # PENTING: Path absolut gaya OS (mis. "/etc/passwd" atau "C:\Windows") harus
    # ditolak total, JANGAN digabung begitu saja, karena pathlib akan menggantikan
    # base path sepenuhnya kalau bagian kedua adalah path absolut
    # (Path("/a") / "/b" == Path("/b")). Strip semua leading slash/backslash dan
    # drive letter Windows (mis. "C:") supaya path selalu diperlakukan sebagai
    # relatif, baik terhadap base maupun workspace_root.
    relative_path = relative_path.strip("/\\")
    if len(relative_path) >= 2 and relative_path[1] == ":":
        # Buang drive letter gaya Windows, contoh "C:\Windows" -> "Windows"
        relative_path = relative_path[2:].strip("/\\")

    anchor = workspace_root if is_explicitly_from_workspace_root else base

    # Gabungkan dengan anchor, lalu resolve untuk menormalkan ../ dsb
    candidate = (anchor / relative_path).resolve()

    # Cek: apakah candidate masih di dalam workspace_root?
    # (Selalu dicek terhadap workspace_root, bukan base, supaya "cd" berulang
    # ke folder lain tetap tidak bisa mengeluarkan kita dari sandbox.)
    try:
        candidate.relative_to(workspace_root)
    except ValueError:
        raise SandboxViolationError(
            f"Akses ditolak: '{relative_path}' mengarah ke luar workspace yang diizinkan "
            f"({workspace_root}). Ferxvis hanya boleh bekerja di dalam folder home ini."
        )

    return candidate


def _display_path(target: Path) -> str:
    """Path relatif terhadap workspace, untuk ditampilkan di pesan ke user (akurat, bukan input mentah)."""
    workspace_root = Path(WORKSPACE_DIR).resolve()
    rel = target.relative_to(workspace_root)
    return str(rel) if str(rel) != "." else "(folder utama workspace)"


def change_directory(relative_path: str = "") -> str:
    """
    Pindahkan "folder kerja saat ini" Ferxvis ke subfolder tertentu di dalam
    workspace (home folder). Semua pemanggilan tool file lain setelah ini
    (list_files, write_note, move_file, dst dengan relative_path biasa, tanpa
    diawali "/") akan dihitung relatif terhadap folder baru ini.

    relative_path="" atau "/" akan mengembalikan ke folder utama workspace.
    """
    global _current_dir
    try:
        target = resolve_safe_path(relative_path, base=_current_dir)
    except SandboxViolationError as e:
        return f"ERROR: {e}"

    if not target.exists():
        return f"ERROR: Folder '{relative_path or '.'}' tidak ditemukan di workspace, current directory tidak berubah."
    if not target.is_dir():
        return f"ERROR: '{relative_path}' adalah file, bukan folder. Current directory tidak berubah."

    _current_dir = target
    return f"Current directory berhasil dipindah ke '{_display_path(target)}'."


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
