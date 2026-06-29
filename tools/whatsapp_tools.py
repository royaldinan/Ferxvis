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

PENTING (fix versi ini):
- Browser dibuka SEKALI dan dipakai ulang (singleton module-level), supaya
  tidak buka tab/Chrome process baru tiap kali kirim pesan (yang bikin profile
  lock collision dan "stuck di tab baru").
- Tidak ada lagi klaim sukses tanpa verifikasi. Sebelum klaim "terkirim",
  tool ini menghitung jumlah bubble pesan keluar (message-out) di chat
  SEBELUM dan SETELAH kirim, dan menunggu sampai jumlahnya bertambah.
  Kalau tidak bisa dipastikan bertambah, tool ini akan bilang TIDAK BISA
  DIPASTIKAN / GAGAL — bukan asumsi "sudah terkirim".
"""

import time
import urllib.parse

from config import WHATSAPP_PROFILE_DIR, WHATSAPP_WAIT_TIME

# ── Singleton driver state ──────────────────────────────────────
# Modul-level, supaya semua panggilan send_whatsapp_message berikutnya
# REUSE browser yang sama, bukan buka Chrome process baru tiap kali.
_driver = None


def _normalize_phone(to: str) -> str:
    """Normalisasi nomor ke format internasional tanpa '+', contoh: 6281286799319."""
    phone = to.replace("+", "").replace(" ", "").replace("-", "")
    if phone.startswith("0"):
        phone = "62" + phone[1:]
    return phone


def _is_driver_alive(driver) -> bool:
    """Cek apakah driver/browser masih hidup dan responsif."""
    if driver is None:
        return False
    try:
        _ = driver.window_handles
        return True
    except Exception:
        return False


def _get_driver():
    """Buka Chrome (sekali) atau reuse instance yang sudah berjalan."""
    global _driver

    if _is_driver_alive(_driver):
        return _driver

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except ImportError:
        raise ImportError(
            "Selenium belum terinstall. Jalankan:\n"
            "pip3 install selenium --break-system-packages\n"
            "Pastikan juga Google Chrome / Chromium dan chromedriver sudah terinstall."
        )

    # Driver lama (kalau ada tapi sudah mati/crash) dibersihkan dulu.
    if _driver is not None:
        try:
            _driver.quit()
        except Exception:
            pass
        _driver = None

    options = Options()
    options.add_argument(f"user-data-dir={WHATSAPP_PROFILE_DIR}")
    options.add_argument("--profile-directory=Default")
    # Headless TIDAK dipakai secara default — supaya user bisa lihat & scan QR
    # pertama kali, dan supaya proses kirim lebih bisa dipantau/dipercaya.
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=900,700")
    # Hindari Chrome nyoba restore session lama / nampilin popup "Chrome ditutup paksa"
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")

    # ── Anti-deteksi automation ──────────────────────────────────
    # WhatsApp Web bisa diam-diam menolak render UI (halaman blank selamanya,
    # tanpa error) kalau mendeteksi browser dikontrol Selenium lewat
    # navigator.webdriver=true atau banner "Chrome is being controlled by
    # automated test software". Opsi-opsi di bawah menghilangkan sinyal itu.
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    _driver = webdriver.Chrome(options=options)

    # Patch tambahan: paksa navigator.webdriver jadi undefined di setiap
    # halaman baru yang dimuat (sebelum script WhatsApp Web sempat jalan).
    try:
        _driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                """
            },
        )
    except Exception:
        # Kalau CDP gagal (versi chromedriver tertentu), lanjut tanpa patch ini —
        # opsi di atas (excludeSwitches, disable-blink-features) tetap jalan.
        pass

    return _driver


def close_whatsapp_session() -> str:
    """Tutup browser WhatsApp Web yang aktif. Dipakai kalau session stuck/error
    dan perlu mulai dari awal (Chrome process baru, profile lock dilepas)."""
    global _driver
    if _driver is None:
        return "ℹ️ Tidak ada sesi WhatsApp Web yang aktif untuk ditutup."
    try:
        _driver.quit()
    except Exception:
        pass
    finally:
        _driver = None
    return "✅ Sesi WhatsApp Web ditutup. Kirim pesan lagi untuk membuka sesi baru."


def _get_compose_box(driver, By):
    """Ambil elemen compose box (kotak ketik pesan) yang sedang aktif."""
    return driver.find_element(
        By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'
    )


def _count_message_rows(driver, By) -> int:
    """Hitung jumlah baris pesan (row) di chat yang lagi terbuka.

    WhatsApp Web sering mengganti nama class internalnya (mis. 'message-out'
    sudah tidak valid di versi terbaru), jadi di sini kita pakai
    `[role="row"]` di dalam container pesan — role ARIA jauh lebih stabil
    daripada hashed class name, karena dipakai untuk accessibility dan
    jarang diganti walau WhatsApp redesign UI-nya.
    """
    try:
        elements = driver.find_elements(
            By.CSS_SELECTOR, 'div[role="application"] div[role="row"]'
        )
        if elements:
            return len(elements)
        # Fallback kalau role="application" tidak ditemukan: cari role="row" global.
        elements = driver.find_elements(By.CSS_SELECTOR, 'div[role="row"]')
        return len(elements)
    except Exception:
        return -1  # -1 artinya gagal menghitung (struktur DOM beda dari ekspektasi)


def send_whatsapp_message(to: str, message: str) -> str:
    """Kirim pesan WhatsApp lewat WhatsApp Web (nomor pribadi user), dengan
    verifikasi nyata sebelum mengklaim sukses."""
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

    try:
        driver = _get_driver()
        driver.get(url)

        wait = WebDriverWait(driver, WHATSAPP_WAIT_TIME)

        # Tunggu compose box / chat termuat dulu (tanda chat sudah dibuka).
        try:
            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
                )
            )
        except Exception:
            # Halaman gagal load (sering: blank page karena WhatsApp Web
            # sempat menolak render saat baru terdeteksi automation, sebelum
            # patch anti-deteksi sempat berlaku). Coba SEKALI lagi via refresh
            # sebelum menyerah — kalau ini juga gagal, baru benar-benar GAGAL.
            try:
                driver.refresh()
                wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
                    )
                )
            except Exception:
                return (
                    f"❌ GAGAL: chat dengan {to} tidak termuat (sudah dicoba 2x, termasuk "
                    f"refresh) dalam {WHATSAPP_WAIT_TIME} detik per percobaan. Kemungkinan "
                    "belum scan QR code, koneksi lambat, nomor tidak valid/tidak terdaftar "
                    "di WhatsApp, atau halaman blank. Cek jendela Chrome yang terbuka, atau "
                    "panggil close_whatsapp_session lalu coba lagi dari awal."
                )

        time.sleep(1.5)  # beri waktu UI/compose box stabil sebelum diukur & diklik

        # ── Baseline SEBELUM kirim (untuk verifikasi sesudahnya) ──
        rows_before = _count_message_rows(driver, By)
        try:
            compose_text_before = _get_compose_box(driver, By).text
        except Exception:
            compose_text_before = None

        # Kasus edge penting: kalau compose box KOSONG dari awal (bukan terisi
        # pesan dari parameter URL), berarti WhatsApp Web gagal mem-prefill teks
        # sama sekali — kalau lanjut klik kirim, yang terkirim bisa jadi pesan
        # kosong/tidak terkirim apa-apa. Deteksi ini secara eksplisit.
        compose_was_prefilled = bool(compose_text_before and compose_text_before.strip())

        sent_click = False
        try:
            send_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Send"]'))
            )
            send_button.click()
            sent_click = True
        except Exception:
            # Fallback: fokus ke compose box lalu tekan Enter
            try:
                compose_box = _get_compose_box(driver, By)
                compose_box.click()
                time.sleep(0.3)
                compose_box.send_keys(Keys.ENTER)
                sent_click = True
            except Exception:
                sent_click = False

        if not sent_click:
            return (
                f"❌ GAGAL: tidak bisa menemukan tombol kirim atau compose box untuk {to}. "
                "Pesan TIDAK terkirim. Jangan anggap ini sukses."
            )

        if not compose_was_prefilled:
            return (
                f"❌ GAGAL: compose box untuk {to} kosong sebelum tombol kirim diklik "
                "(pesan tidak ter-prefill dari WhatsApp Web). Klik kirim sudah terjadi "
                "tapi kemungkinan tidak ada teks yang benar-benar terkirim. Anggap "
                "pesan BELUM terkirim — coba lagi atau cek manual di jendela Chrome."
            )

        # ── Verifikasi nyata, pakai DUA sinyal independen ──
        # Sinyal A: compose box jadi kosong (WhatsApp selalu mengosongkan
        #           kotak ketik setelah pesan benar-benar terkirim).
        # Sinyal B: jumlah baris pesan (role="row") di chat bertambah.
        # Kalau salah satu kedeteksi, anggap terverifikasi — supaya kalau satu
        # sinyal gagal terbaca karena perubahan struktur DOM, masih ada cadangan.
        verified = False
        verified_signal = None
        for _ in range(10):  # polling ~5 detik
            time.sleep(0.5)

            if compose_text_before is not None:
                try:
                    compose_text_now = _get_compose_box(driver, By).text
                    if compose_text_now == "" and compose_text_before != "":
                        verified = True
                        verified_signal = "compose box kosong setelah kirim"
                        break
                except Exception:
                    pass

            if rows_before >= 0:
                rows_now = _count_message_rows(driver, By)
                if rows_now > rows_before:
                    verified = True
                    verified_signal = "jumlah baris pesan bertambah"
                    break

        if verified:
            return f"✅ TERVERIFIKASI terkirim ke {to} (lewat WhatsApp Web) — sinyal: {verified_signal}."
        else:
            return (
                f"⚠️ TIDAK BISA DIPASTIKAN apakah pesan ke {to} benar-benar terkirim. "
                "Klik kirim sudah dilakukan, tapi tidak ada sinyal (compose box kosong / "
                "jumlah baris pesan bertambah) yang terkonfirmasi dalam waktu tunggu. "
                "Anggap BELUM terkirim sampai dicek manual — cek jendela Chrome yang "
                "terbuka untuk pastikan."
            )

    except Exception as e:
        return (
            f"❌ ERROR kirim WhatsApp: {e}\n"
            "Kemungkinan sebab: belum scan QR code, koneksi internet lambat, "
            "atau struktur WhatsApp Web berubah. Anggap pesan BELUM terkirim. "
            "Coba lagi, atau panggil close_whatsapp_session kalau browser stuck."
        )
    # Catatan: TIDAK ADA driver.quit() di sini lagi (singleton, dipakai ulang).
    # Untuk menutup browser secara manual, gunakan tool close_whatsapp_session().
