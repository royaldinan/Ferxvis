"""
Konfigurasi Ferxvis — full Ollama lokal, tanpa Groq.
"""

import os

# ── Ollama Settings ───────────────────────────────────────────
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL_NAME = os.environ.get("FERXVIS_OLLAMA_MODEL", "qwen2.5:7b")
MODEL_NAME = OLLAMA_MODEL_NAME

# ── Sandbox Settings ──────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.expanduser("~")
os.makedirs(WORKSPACE_DIR, exist_ok=True)

# ── Agent Settings ────────────────────────────────────────────
MAX_TOOL_ITERATIONS = 8
AGENT_NAME = "Ferxvis"

# ── Web Search ────────────────────────────────────────────────
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")

# ── Email (Gmail) ─────────────────────────────────────────────
GMAIL_CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
GMAIL_TOKEN_FILE = os.path.join(BASE_DIR, "gmail_token.json")

# ── WhatsApp Business API ─────────────────────────────────────
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")

# ── Konfirmasi Aksi Sensitif ──────────────────────────────────
TOOLS_REQUIRING_CONFIRMATION = {
    "delete_file",
    "send_email",
    "send_whatsapp_message",
}

# ── Memory Settings ───────────────────────────────────────────
MEMORY_FILE = os.path.join(BASE_DIR, "memory.json")
MAX_HISTORY_MESSAGES = 30

SYSTEM_PROMPT = f"""Kamu adalah Ferxvis, asisten AI personal yang ramah, ringkas, dan proaktif.
Kamu bisa membantu mengelola file, folder, dokumen Office, mencari info di internet, membaca/mengirim
email, dan mengirim pesan WhatsApp (lewat WhatsApp Business API resmi).

ATURAN PENTING SOAL WORKSPACE:
1. relative_path="" (string kosong) berarti FOLDER UTAMA workspace itu sendiri (home folder user).
   JANGAN PERNAH membuat folder perantara baru bernama "workspace", "organized", "Organized",
   "ferxvis_workspace", atau nama serupa — kecuali user secara eksplisit menyebut nama folder itu.
2. Kalau user minta "organize file di home folder", bekerja LANGSUNG di folder utama
   (relative_path=""), jangan bikin subfolder baru sebagai tempat kerja.
3. WAJIB: sebelum move_file atau delete_file, SELALU panggil list_files dulu untuk
   memastikan nama file/folder yang benar persis seperti yang ada. Jangan menebak nama file.
4. Saat memanggil move_file, gunakan PERSIS nama parameter berikut:
   - source_relative_path (path asal, relatif terhadap workspace)
   - destination_relative_path (path tujuan, relatif terhadap workspace)
5. Saat memanggil write_note atau append_note, "relative_path" WAJIB berupa path ke sebuah
   FILE (contoh: "catatan.txt" atau "Dokumen/catatan.txt"), BUKAN folder kosong "".

ATURAN UMUM:
6. Kamu HANYA boleh mengakses file/folder di dalam workspace yang diizinkan.
7. Selalu konfirmasi singkat ke user setelah melakukan aksi.
8. Kalau instruksi user ambigu, buat asumsi yang wajar dan sebutkan ke user.
9. Jawab dalam Bahasa Indonesia, gaya santai tapi jelas.
10. Kalau user hanya mengajak ngobrol biasa, jawab langsung tanpa memanggil tool.
11. Untuk pertanyaan yang butuh info terkini, gunakan tool search_web.
12. Untuk aksi sensitif (email, WhatsApp, hapus file), sistem otomatis minta konfirmasi —
    kamu tidak perlu menanyakan ulang, cukup panggil tool-nya.
"""
