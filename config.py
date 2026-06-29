"""
Konfigurasi Ferxvis v2.0
"""

import os

# ── Ollama (offline fallback) ──────────────────────────────────
OLLAMA_HOST = "http://localhost:11434"
MODEL_NAME = "qwen2.5:7b"

# ── Groq API (online, gratis, cepat) ──────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")

# Model tersedia di Groq free tier (update Juni 2025):
# - llama-3.3-70b-versatile   → chat umum, tool calling, CEPAT
# - llama3-8b-8192             → ringan, tool calling
# - llama-3.2-90b-vision-preview → vision (gambar)
# - llava-v1.5-7b-4096-preview   → vision alternatif
GROQ_MODEL = "llama-3.3-70b-versatile"          # untuk chat + tool calling
GROQ_VISION_MODEL = "llama-3.2-90b-vision-preview"  # untuk analisis gambar

# ── Gemini (tidak dipakai) ────────────────────────────────────
GEMINI_API_KEY = ""
GEMINI_MODEL = ""

# ── Folder Akses ───────────────────────────────────────────────
HOME_DIR = os.path.expanduser("~")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = HOME_DIR  # Akses penuh ke semua folder

os.makedirs(WORKSPACE_DIR, exist_ok=True)

# ── Agent ─────────────────────────────────────────────────────
MAX_TOOL_ITERATIONS = 10
AGENT_NAME = "Ferxvis"

# ── Email (akun Google) ─────────────────────────────────────────
# Struktur tetap multi-akun (dict) supaya mudah nambah akun lain nanti,
# tapi saat ini hanya akun personal yang aktif dipakai.
EMAIL_ACCOUNTS = {
    "personal": {
        "address": "ferdinandmanurungcr7@gmail.com",
        "credentials_file": os.path.join(BASE_DIR, "credentials_personal.json"),
        "token_file": os.path.join(BASE_DIR, "gmail_token_personal.json"),
    },
    # Akun kampus (student.president.ac.id) di-skip dulu — kalau mau aktifkan lagi,
    # uncomment blok ini dan siapkan credentials_kampus.json:
    # "kampus": {
    #     "address": "ferdinand.manurung@student.president.ac.id",
    #     "credentials_file": os.path.join(BASE_DIR, "credentials_kampus.json"),
    #     "token_file": os.path.join(BASE_DIR, "gmail_token_kampus.json"),
    # },
}
DEFAULT_EMAIL_ACCOUNT = "personal"

# Backward-compat (dipakai kalau ada kode lama yang masih refer ke variabel lama)
GMAIL_CREDENTIALS_FILE = EMAIL_ACCOUNTS[DEFAULT_EMAIL_ACCOUNT]["credentials_file"]
GMAIL_TOKEN_FILE = EMAIL_ACCOUNTS[DEFAULT_EMAIL_ACCOUNT]["token_file"]

# ── WhatsApp (WhatsApp Web automation, bukan Meta Business API) ─
# Pakai nomor WA pribadi (081286799319 / +62 812-8679-9319) lewat WhatsApp Web.
# Scan QR code SEKALI saat pertama kali jalan, lalu session tersimpan di
# WHATSAPP_PROFILE_DIR sehingga tidak perlu scan ulang setiap kali.
WHATSAPP_PHONE_NUMBER = "+6281286799319"
WHATSAPP_PROFILE_DIR = os.path.join(BASE_DIR, "whatsapp_session")
os.makedirs(WHATSAPP_PROFILE_DIR, exist_ok=True)
WHATSAPP_WAIT_TIME = 25  # detik, waktu tunggu WhatsApp Web load & kirim pesan

# ── Konfirmasi aksi sensitif ───────────────────────────────────
TOOLS_REQUIRING_CONFIRMATION = {
    "delete_file",
    "send_email",
    "send_whatsapp_message",
}

# ── Memory & History ──────────────────────────────────────────
MEMORY_FILE = os.path.join(BASE_DIR, "memory.json")
CHAT_HISTORY_DIR = os.path.join(BASE_DIR, "chat_histories")
SAVED_CLIPBOARD_FILE = os.path.join(BASE_DIR, "saved_clipboard.json")
MAX_HISTORY_MESSAGES = 50

os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)

SYSTEM_PROMPT = f"""Kamu adalah {AGENT_NAME}, asisten AI personal cerdas milik Ferdinand (Ferxan).
Kamu bisa bantu kelola file/folder di seluruh komputer, dokumen Office, cari info terkini,
baca/kirim email Gmail, kirim WhatsApp lewat WhatsApp Web, dan analisis gambar.

ATURAN:
1. Akses penuh ke seluruh folder home user. Gunakan path absolut kalau user sebut folder spesifik.
2. Konfirmasi singkat setelah aksi berhasil.
3. Kalau instruksi ambigu, buat asumsi wajar dan sebutkan.
4. Jawab dalam Bahasa Indonesia, santai tapi jelas dan cerdas.
5. Untuk info terkini, gunakan search_web.
6. Aksi sensitif (kirim email, kirim WA, hapus file) otomatis minta konfirmasi.
7. Kalau user kirim gambar, analisis dengan seksama.
8. Kirim WhatsApp menggunakan nomor pribadi user via WhatsApp Web — pastikan user paham ini akan membuka jendela browser sebentar untuk mengirim pesan.
9. Kepribadian: cerdas, efisien, sedikit humor, selalu membantu.
"""
