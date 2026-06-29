"""
Script diagnostik OAuth Google — jalankan ini LANGSUNG di terminal
(bukan lewat Ferxvis GUI), supaya kalau ada error, full traceback-nya
kelihatan utuh di console, gak ketelan sama try/except di email_tools.py.

Cara pakai:
    cd ~/Downloads/ferxvis/ferxvis
    python3 diagnose_oauth.py
"""

import os
import sys

# Pastikan bisa import config.py dari folder ferxvis
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import EMAIL_ACCOUNTS, DEFAULT_EMAIL_ACCOUNT

info = EMAIL_ACCOUNTS[DEFAULT_EMAIL_ACCOUNT]
creds_file = info["credentials_file"]
token_file = info["token_file"]

print(f"Akun        : {info['address']}")
print(f"creds_file  : {creds_file}  (exists={os.path.exists(creds_file)})")
print(f"token_file  : {token_file}  (exists={os.path.exists(token_file)})")
print()

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

print(">>> Membuat flow dari client secrets file...")
flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)

print(">>> Memanggil run_local_server(port=8765, timeout_seconds=120)...")
print(">>> Kalau browser kebuka, SEGERA login dan klik 'Lanjutkan'/'Allow'.")
print(">>> Tunggu di sini sampai muncul 'BERHASIL' atau error di bawah.")
print()

try:
    creds = flow.run_local_server(port=8765, timeout_seconds=120, open_browser=True)
    print()
    print("=== BERHASIL ===")
    print("Token didapat. Menyimpan ke", token_file)
    with open(token_file, "w") as f:
        f.write(creds.to_json())
    print("Token tersimpan. Gmail seharusnya sudah bisa dipakai dari Ferxvis.")
except Exception as e:
    print()
    print("=== GAGAL — TRACEBACK LENGKAP DI BAWAH ===")
    import traceback
    traceback.print_exc()
