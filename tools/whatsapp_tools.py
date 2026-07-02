"""
Tool untuk mengirim & membaca pesan WhatsApp lewat WhatsApp Business Cloud API resmi (Meta).

PENTING: ini SENGAJA tidak menggunakan library unofficial (whatsapp-web.js, Baileys, dll)
yang otomasi akun WhatsApp personal, karena itu melanggar Terms of Service WhatsApp dan
berisiko akun kamu di-ban permanen.

WhatsApp Business Cloud API resmi butuh setup akun bisnis Meta - lihat README.md bagian
'Setup WhatsApp' untuk langkah lengkapnya.

send_whatsapp_message ada di TOOLS_REQUIRING_CONFIRMATION (config.py), jadi akan selalu
minta konfirmasi user dulu sebelum benar-benar terkirim.
"""

import json
import urllib.request
import urllib.error

from config import WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID

GRAPH_API_VERSION = "v20.0"


def _is_configured() -> bool:
    return bool(WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID)


def send_whatsapp_message(to: str, message: str) -> str:
    """
    Kirim pesan teks WhatsApp ke nomor tujuan lewat WhatsApp Business Cloud API.
    to: nomor tujuan dalam format internasional tanpa tanda '+', contoh '6281234567890'.
    """
    if not _is_configured():
        return (
            "ERROR: WhatsApp Business API belum dikonfigurasi. Set environment variable "
            "WHATSAPP_ACCESS_TOKEN dan WHATSAPP_PHONE_NUMBER_ID. Lihat README.md bagian "
            "'Setup WhatsApp' untuk cara mendapatkan kredensial dari Meta for Developers."
        )

    to_clean = "".join(ch for ch in to if ch.isdigit())
    if not to_clean or len(to_clean) < 8:
        return f"ERROR: nomor tujuan '{to}' tidak valid. Gunakan format internasional, contoh '6281234567890'."

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_clean,
        "type": "text",
        "text": {"body": message},
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            msg_id = result.get("messages", [{}])[0].get("id", "")
            return f"Pesan WhatsApp berhasil dikirim ke {to_clean} (id: {msg_id})."
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        try:
            err_json = json.loads(body)
            err_msg = err_json.get("error", {}).get("message", body)
        except json.JSONDecodeError:
            err_msg = body
        if e.code == 401:
            return "ERROR: Access token WhatsApp tidak valid atau sudah expired."
        return f"ERROR: WhatsApp API mengembalikan error: {err_msg}"
    except urllib.error.URLError as e:
        return f"ERROR: Tidak bisa terhubung ke WhatsApp API. Cek koneksi internet. Detail: {e}"
    except Exception as e:
        return f"ERROR saat mengirim pesan WhatsApp: {e}"
