"""
WhatsApp tools - via WhatsApp Web automation (Selenium), BUKAN Meta Business API.

⚠️ PERINGATAN PENTING:
Menggunakan automasi browser untuk WhatsApp Web dengan nomor pribadi melanggar
Terms of Service WhatsApp. Mengirim pesan terlalu cepat/banyak berisiko nomor
diblokir permanen oleh WhatsApp. Gunakan secara wajar (jangan spam, beri jeda
antar pesan, jangan kirim ke banyak nomor sekaligus dalam waktu singkat).

Cara kerja:
1. Pertama kali jalan: Chrome akan terbuka menampilkan QR code WhatsApp Web.
   Scan dengan WhatsApp di HP (Linked Devices > Link a Device).
2. Session disimpan di folder config.WHATSAPP_PROFILE_DIR, jadi run berikutnya
   tidak perlu scan ulang (selama tidak logout manual / WhatsApp tidak logout
   otomatis karena lama tidak dipakai).
"""

import time
import urllib.parse

from config import WHATSAPP_PROFILE_DIR, WHATSAPP_WAIT_TIME


def _normalize_phone(to: str) -> str:
    """Normalisasi nomor ke format internasional tanpa '+', contoh: 6281286799319."""
    phone = to.replace("+", "").replace(" ", "").replace("-", "")
    if phone.startswith("0"):
        phone = "62" + phone[1:]
    return phone


def _get_driver():
    """Buka/reuse Chrome dengan profile persisten untuk WhatsApp Web."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except ImportError:
        raise ImportError(
            "Selenium belum terinstall. Jalankan:\n"
            "pip3 install selenium --break-system-packages\n"
            "Pastikan juga Google Chrome / Chromium dan chromedriver sudah terinstall."
        )

    options = Options()
    options.add_argument(f"user-data-dir={WHATSAPP_PROFILE_DIR}")
    options.add_argument("--profile-directory=Default")
    # Headless TIDAK dipakai secara default — supaya user bisa lihat & scan QR
    # pertama kali, dan supaya proses kirim lebih bisa dipantau/dipercaya.
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=900,700")

    driver = webdriver.Chrome(options=options)
    return driver


def send_whatsapp_message(to: str, message: str) -> str:
    """Kirim pesan WhatsApp lewat WhatsApp Web (nomor pribadi user)."""
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        return (
            "❌ Selenium belum terinstall.\n"
            "Jalankan: pip3 install selenium --break-system-packages\n"
            "Dan pastikan Google Chrome + chromedriver sudah terinstall di sistem."
        )

    phone = _normalize_phone(to)
    encoded_msg = urllib.parse.quote(message)
    url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_msg}"

    driver = None
    try:
        driver = _get_driver()
        driver.get(url)

        wait = WebDriverWait(driver, WHATSAPP_WAIT_TIME)

        # Tunggu sampai kotak chat termuat (elemen "compose box" / send button siap).
        # Selector ini berbasis struktur WhatsApp Web yang bisa berubah seiring update mereka;
        # kalau gagal, fallback ke pengiriman manual via tombol Enter.
        try:
            send_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Send"]'))
            )
            time.sleep(1.5)  # beri waktu UI stabil sebelum klik
            send_button.click()
        except Exception:
            # Fallback: fokus ke compose box lalu tekan Enter
            compose_box = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
                )
            )
            compose_box.click()
            time.sleep(0.5)
            compose_box.send_keys(Keys.ENTER)

        time.sleep(2)  # pastikan pesan terkirim sebelum tab ditutup
        return f"✅ Pesan WhatsApp berhasil dikirim ke {to} (lewat WhatsApp Web)."

    except Exception as e:
        return (
            f"ERROR kirim WhatsApp: {e}\n"
            "Kemungkinan sebab: belum scan QR code, koneksi internet lambat, "
            "atau struktur WhatsApp Web berubah. Coba lagi atau cek jendela Chrome yang terbuka."
        )
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
