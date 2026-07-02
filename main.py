"""
Ferxvis - Asisten AI Lokal
===========================
Jalankan file ini untuk membuka aplikasi.

    python main.py
"""

import sys

# Inisialisasi folder __init__.py kalau dijalankan pertama kali (lihat setup di README)
from gui.chat_window import run_gui


def main():
    print("Memulai Ferxvis...")
    run_gui()


if __name__ == "__main__":
    main()
