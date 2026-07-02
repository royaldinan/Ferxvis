"""
Telegram tools untuk Ferxvis - kirim & terima pesan via Bot API resmi.
"""

import json
import urllib.request
import urllib.error
import threading
import time

TELEGRAM_TOKEN = "8935519154:AAHYBnAwBSGt9EPzgWj5kKdjAid5dLHy4Sw"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Cache chat_id user pertama yang kirim pesan ke bot
_user_chat_id = None
_last_update_id = 0


def _request(endpoint: str, payload: dict = None) -> dict:
    url = f"{TELEGRAM_API}/{endpoint}"
    data = json.dumps(payload or {}).encode("utf-8") if payload else None
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method="POST" if data else "GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_telegram_message(chat_id: str, message: str) -> str:
    """Kirim pesan teks ke chat_id Telegram tertentu."""
    if not chat_id:
        # Coba pakai chat_id yang sudah di-cache
        global _user_chat_id
        if not _user_chat_id:
            return "ERROR: Belum ada user yang menghubungi bot. Minta Ferdinand kirim /start ke bot dulu."
        chat_id = _user_chat_id

    result = _request("sendMessage", {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    })
    if result.get("ok"):
        return f"✅ Pesan Telegram berhasil dikirim ke {chat_id}."
    return f"ERROR Telegram: {result.get('description', result.get('error', 'Unknown'))}"


def send_telegram_to_me(message: str) -> str:
    """Kirim pesan ke Ferdinand (chat_id yang sudah terdaftar)."""
    global _user_chat_id
    if not _user_chat_id:
        return "ERROR: Ferdinand belum pernah /start bot. Buka Telegram, cari bot kamu, kirim /start."
    return send_telegram_message(_user_chat_id, message)


def get_telegram_messages(max_results: int = 5) -> str:
    """Ambil pesan terbaru yang masuk ke bot."""
    global _last_update_id, _user_chat_id
    result = _request("getUpdates", {
        "offset": _last_update_id + 1,
        "limit": max_results,
        "timeout": 0,
    })
    if not result.get("ok"):
        return f"ERROR: {result.get('description', 'Gagal ambil pesan')}"

    updates = result.get("result", [])
    if not updates:
        return "Tidak ada pesan baru di Telegram."

    lines = []
    for upd in updates:
        _last_update_id = max(_last_update_id, upd.get("update_id", 0))
        msg = upd.get("message", {})
        if not msg:
            continue
        sender = msg.get("from", {})
        name = sender.get("first_name", "?")
        username = sender.get("username", "")
        chat_id = msg.get("chat", {}).get("id")
        text = msg.get("text", "(bukan teks)")
        date = msg.get("date", 0)

        # Auto-cache chat_id Ferdinand
        if chat_id and not _user_chat_id:
            _user_chat_id = str(chat_id)

        lines.append(f"👤 {name} (@{username}) [chat_id: {chat_id}]\n💬 {text}")

    return "\n\n".join(lines) if lines else "Tidak ada pesan teks baru."


def get_bot_info() -> str:
    """Cek info bot Telegram."""
    result = _request("getMe")
    if result.get("ok"):
        bot = result["result"]
        return (f"Bot: @{bot.get('username')} ({bot.get('first_name')})\n"
                f"Chat link: t.me/{bot.get('username')}")
    return f"ERROR: {result.get('description', 'Gagal ambil info bot')}"


def start_polling(on_message_callback=None):
    """Background polling untuk terima pesan real-time (opsional)."""
    global _last_update_id, _user_chat_id

    def poll():
        global _last_update_id, _user_chat_id
        while True:
            try:
                result = _request("getUpdates", {
                    "offset": _last_update_id + 1,
                    "limit": 10,
                    "timeout": 20,
                })
                if result.get("ok"):
                    for upd in result.get("result", []):
                        _last_update_id = max(_last_update_id, upd.get("update_id", 0))
                        msg = upd.get("message", {})
                        if msg:
                            chat_id = str(msg.get("chat", {}).get("id", ""))
                            if chat_id and not _user_chat_id:
                                _user_chat_id = chat_id
                            if on_message_callback:
                                on_message_callback(msg)
            except Exception:
                pass
            time.sleep(1)

    t = threading.Thread(target=poll, daemon=True)
    t.start()
