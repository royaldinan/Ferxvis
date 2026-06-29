# 🤖 Ferxvis — Asisten AI Lokal

Ferxvis adalah asisten AI personal yang jalan 100% di laptop kamu lewat LLM lokal (Qwen).
Dia bisa mengelola catatan/file/folder, membuat dokumen Word & Excel, mencari info terkini
di internet, membaca & mengirim email, dan mengirim pesan WhatsApp — semua lewat chat
natural language di GUI sederhana.

---

## ✅ Status Setiap Fitur (baca ini dulu)

Supaya jelas, ini status pengujian masing-masing bagian:

| Fitur | Status pengujian |
|---|---|
| Core agent + tool-calling loop | ✅ Diuji penuh (mock LLM, berbagai skenario) |
| File & folder management (sandbox) | ✅ Diuji penuh, termasuk 7 teknik bypass sandbox |
| Dokumen Word & Excel | ✅ Diuji penuh end-to-end |
| GUI chatbot | ✅ Diuji penuh (render headless + simulasi interaksi nyata) |
| Sistem konfirmasi aksi sensitif | ✅ Diuji penuh end-to-end lewat GUI |
| Memory antar sesi | ✅ Diuji penuh (save/load/trim/corrupt-file handling) |
| Web search (Brave API) | ✅ Logic & error handling diuji penuh dengan mock API |
| Email (Gmail) | ✅ Logic & error handling diuji dengan mock API. **Belum** dites dengan akun Gmail asli — proses OAuth butuh browser & login interaktif yang tidak bisa disimulasikan dari sandbox pengujian saya. Kemungkinan besar jalan baik, tapi coba dulu pelan-pelan saat pertama setup. |
| WhatsApp (Business API resmi) | ✅ Logic & error handling diuji dengan mock API. **Belum** dites dengan akun WhatsApp Business asli — butuh approval dari Meta yang di luar kendali saya. |

Singkatnya: **semua yang berjalan lokal di laptop kamu (file, Office, GUI, memory) sudah
divalidasi ketat dan seharusnya jalan tanpa masalah.** Email & WhatsApp logic-nya solid,
tapi koneksi ke API pihak ketiga yang asli baru benar-benar teruji saat kamu coba sendiri.

---

## 📋 Yang Dibutuhkan

1. **Python 3.10+**
2. **Ollama** — https://ollama.com/download
3. *(Opsional)* API key Brave Search — untuk fitur web search
4. *(Opsional)* Google Cloud credentials — untuk fitur email
5. *(Opsional)* WhatsApp Business API access — untuk fitur WhatsApp

Fitur-fitur opsional di atas **tidak wajib**. Tanpa setup tambahan apapun, Ferxvis tetap
bisa mengelola file/folder/dokumen Office sepenuhnya.

---

## 🚀 Instalasi Dasar (Wajib)

### 1. Install Ollama & jalankan
```bash
ollama serve
```
Biarkan terminal ini tetap terbuka.

### 2. Download model Qwen (terminal lain)
```bash
ollama pull qwen2.5:7b
```
> RAM ≤8GB → `qwen2.5:3b` &nbsp;|&nbsp; RAM 16GB → `qwen2.5:7b` (default) &nbsp;|&nbsp; RAM 32GB+ → `qwen2.5:14b`
>
> Ganti pilihan model di `config.py` (`MODEL_NAME`).

### 3. Install dependencies Python
```bash
pip install -r requirements.txt
```

### 4. Jalankan
```bash
python main.py
```

---

## 🔍 Setup Web Search (Opsional)

1. Daftar gratis di https://brave.com/search/api/ (free tier: 2000 query/bulan)
2. Dapatkan API key
3. Set environment variable sebelum jalankan aplikasi:

   **Windows (CMD):**
   ```cmd
   set BRAVE_API_KEY=isi_api_key_kamu
   python main.py
   ```
   **Windows (PowerShell):**
   ```powershell
   $env:BRAVE_API_KEY="isi_api_key_kamu"
   python main.py
   ```
   **Mac/Linux:**
   ```bash
   export BRAVE_API_KEY=isi_api_key_kamu
   python main.py
   ```

Tanpa setup ini, Ferxvis akan kasih tahu kalau kamu minta sesuatu yang butuh pencarian web.

---

## 📧 Setup Email / Gmail (Opsional)

Ferxvis pakai **Gmail API resmi via OAuth** — TIDAK PERNAH menyimpan password asli kamu.

### Langkah setup:
1. Buka https://console.cloud.google.com/ dan buat project baru (gratis)
2. Aktifkan **Gmail API** di menu "APIs & Services" → "Enable APIs and Services"
3. Buat **OAuth consent screen** (pilih "External", isi info dasar - untuk pemakaian
   pribadi cukup tambahkan email kamu sendiri sebagai "test user")
4. Buat **OAuth Client ID**:
   - Menu "Credentials" → "Create Credentials" → "OAuth client ID"
   - Application type: **Desktop app**
   - Download file JSON hasilnya
5. Rename file yang didownload jadi `credentials.json`, letakkan di folder root `ferxvis/`
   (sejajar dengan `main.py`)
6. Jalankan Ferxvis dan minta dia baca/kirim email untuk pertama kali — browser akan
   otomatis terbuka minta kamu login Google & izinkan akses. Setelah ini, token tersimpan
   otomatis di `gmail_token.json` dan tidak akan diminta lagi.

⚠️ **Catatan keamanan:** jangan share file `credentials.json` atau `gmail_token.json` ke
siapapun — keduanya memberi akses ke akun Gmail kamu. File-file ini sebaiknya tidak
di-commit ke Git/GitHub (kalau kamu pakai versioning).

**Catatan penting soal pengiriman email:** `send_email` selalu minta konfirmasi kamu
(klik tombol Ya/Tidak di GUI) sebelum benar-benar terkirim — Ferxvis tidak akan pernah
kirim email tanpa persetujuanmu.

---

## 💬 Setup WhatsApp (Opsional)

Ferxvis menggunakan **WhatsApp Business Cloud API resmi dari Meta**. Saya sengaja
**tidak** menyediakan opsi library unofficial (seperti `whatsapp-web.js` atau `Baileys`)
yang mengotomasi akun WhatsApp pribadi, karena itu melanggar Terms of Service WhatsApp
dan berisiko akun kamu di-ban permanen.

### Langkah setup (resmi via Meta):
1. Buka https://developers.facebook.com/ dan buat akun developer (gratis)
2. Buat App baru, pilih tipe "Business"
3. Di dashboard app, tambahkan produk **WhatsApp**
4. Meta akan kasih kamu nomor test gratis untuk development, plus:
   - **Temporary Access Token** (atau buat System User untuk token permanen)
   - **Phone Number ID**
5. Set environment variable:

   **Mac/Linux:**
   ```bash
   export WHATSAPP_ACCESS_TOKEN=isi_token_kamu
   export WHATSAPP_PHONE_NUMBER_ID=isi_phone_number_id
   python main.py
   ```
   **Windows (PowerShell):**
   ```powershell
   $env:WHATSAPP_ACCESS_TOKEN="isi_token_kamu"
   $env:WHATSAPP_PHONE_NUMBER_ID="isi_phone_number_id"
   python main.py
   ```

### ⚠️ Keterbatasan penting yang perlu kamu tahu:
- **Mengirim pesan**: bisa, dan sudah diimplementasi (`send_whatsapp_message`).
- **Membaca pesan masuk**: WhatsApp Business Cloud API **tidak punya fitur "cek inbox"**
  seperti email. Pesan masuk dikirim lewat *webhook* (server kamu harus punya endpoint
  publik yang menerima notifikasi real-time dari Meta) — ini butuh infrastruktur server
  terpisah (hosting, domain, HTTPS) yang di luar scope aplikasi desktop seperti Ferxvis.
  Kalau kamu butuh fitur ini, itu pengembangan lanjutan yang lebih besar.
- **Nomor test gratis dari Meta** hanya bisa kirim ke nomor yang sudah didaftarkan
  sebagai "test recipient" di dashboard Meta, sampai kamu verifikasi bisnis kamu secara resmi.

`send_whatsapp_message` juga selalu minta konfirmasi kamu dulu sebelum terkirim, sama
seperti email.

---

## 🧠 Memory Antar Sesi

Ferxvis sekarang "ingat" percakapan sebelumnya walau aplikasi ditutup dan dibuka lagi
(disimpan di `memory.json`, otomatis terbatas ke 30 pesan terakhir supaya tidak membengkak).

Klik tombol **"🗑️ Percakapan Baru"** di pojok kanan atas untuk mulai dari nol.

---

## ⚠️ Sistem Konfirmasi Aksi Sensitif

Tiga aksi berikut **selalu** minta konfirmasi eksplisit (tombol Ya/Tidak) sebelum
benar-benar dijalankan, karena dampaknya tidak bisa dibatalkan atau keluar dari laptop kamu:

- `delete_file` — menghapus file/folder
- `send_email` — mengirim email
- `send_whatsapp_message` — mengirim pesan WhatsApp

Ferxvis tidak akan pernah melakukan salah satu dari ini tanpa kamu klik tombol konfirmasi
secara aktif. Daftar ini bisa diubah di `config.py` (`TOOLS_REQUIRING_CONFIRMATION`) kalau
kamu mau menambah aksi lain yang perlu dikonfirmasi.

---

## 🔒 Tentang Keamanan Sandbox

Operasi file (baca, tulis, buat folder, hapus, pindah) dibatasi ketat ke dalam folder
**workspace** (`workspace/` di sebelah `main.py`, bisa diubah lewat `WORKSPACE_DIR` di
`config.py`). Ini sudah ditest melawan 7+ teknik bypass berbeda (path absolut, `../../`,
drive letter Windows, dll) — semua diblokir di fungsi `resolve_safe_path()`.

Tools yang **tidak** terbatas sandbox (karena memang aksesnya ke layanan eksternal, bukan
filesystem) adalah email, WhatsApp, dan web search — masing-masing punya proteksinya
sendiri (konfirmasi user untuk email/WhatsApp, read-only untuk search).

---

## 💬 Contoh yang Bisa Kamu Coba

```
Buat folder "Laporan Mingguan", taruh catatan isinya "Progress 80%"

Buat dokumen Word judul "Proposal" isinya 2 paragraf tentang rencana kolaborasi

Cari info terbaru tentang harga emas hari ini

Baca 5 email terbaru di inbox saya

Kirim email ke budi@example.com subjek "Meeting" isi "Bisa ketemu jam 2 siang?"

Kirim WhatsApp ke 6281234567890 isinya "Halo, jadi meeting jam 2 ya"

Hapus file catatan_lama.txt
```

Untuk 3 contoh terakhir, Ferxvis akan minta konfirmasi dulu sebelum benar-benar dijalankan.

---

## 🛠️ Troubleshooting

**"Ollama tidak terdeteksi"** → pastikan `ollama serve` jalan di terminal lain.

**"Model belum di-pull"** → `ollama pull qwen2.5:7b`.

**GUI tidak muncul** → pastikan `pip install -r requirements.txt` selesai tanpa error.
Di Linux, install dulu: `sudo apt install python3-tk`.

**Web search bilang "belum diaktifkan"** → set `BRAVE_API_KEY` (lihat bagian Setup Web Search).

**Email gagal "credentials.json tidak ditemukan"** → lihat bagian Setup Email, pastikan
file diletakkan tepat di folder root `ferxvis/`.

**Browser tidak terbuka otomatis saat login Gmail pertama kali** → cek terminal, biasanya
ada URL yang bisa dibuka manual kalau auto-open gagal (umum terjadi di environment tanpa
browser default yang terdeteksi, misal lewat SSH/remote desktop tertentu).

**WhatsApp error 401** → access token sudah expired (token sementara dari Meta biasanya
cuma berlaku 24 jam kalau bukan System User token permanen) — generate ulang di dashboard Meta.

**Respons lambat** → normal untuk LLM lokal, terutama pertama kali load model. Coba model
lebih kecil (`qwen2.5:3b`) kalau terlalu lambat.

---

## 🗺️ Status Roadmap

| Tahap | Fitur | Status |
|---|---|---|
| 0 | Setup Ollama + Qwen | ✅ |
| 1 | Core agent + GUI Chatbot | ✅ |
| 2 | File & folder tools (sandbox) | ✅ |
| 3 | Microsoft Office tools | ✅ |
| 4 | Web search | ✅ |
| 5 | Email (Gmail) | ✅ (logic teruji, butuh testing akun asli oleh kamu) |
| 6 | WhatsApp (Business API resmi) | ✅ (logic teruji, butuh approval Meta + testing akun asli) |
| 7 | Memory + konfirmasi aksi sensitif | ✅ |

**Pengembangan lanjutan yang mungkin diminati di masa depan** (di luar scope sesi ini):
- Webhook server untuk menerima pesan WhatsApp masuk secara real-time
- Settings panel di GUI (atur API key, model, workspace path langsung dari aplikasi,
  tanpa edit `config.py` manual)
- Voice input/output (text-to-speech, speech-to-text)
- Multi-step task scheduling (misal "ingatkan saya besok jam 9")

---

## 📁 Struktur Proyek

```
ferxvis/
├── main.py
├── config.py
├── requirements.txt
├── memory.json                 # Auto-generated, histori percakapan
├── credentials.json            # Kamu tambahkan manual (lihat Setup Email)
├── gmail_token.json             # Auto-generated setelah login Gmail pertama kali
├── core/
│   ├── agent.py                # Agent loop + sistem konfirmasi
│   ├── llm_client.py            # Koneksi ke Ollama
│   └── memory.py                # Simpan/load histori percakapan
├── tools/
│   ├── file_tools.py            # Operasi file/folder (sandbox)
│   ├── office_tools.py          # Word & Excel
│   ├── web_tools.py              # Web search
│   ├── email_tools.py            # Gmail
│   ├── whatsapp_tools.py         # WhatsApp Business API
│   └── registry.py               # Daftar tool + dispatcher
├── gui/
│   └── chat_window.py            # GUI chatbot + UI konfirmasi
└── workspace/                     # Sandbox folder kerja
```
