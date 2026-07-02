"""
Agent Core - otak Ferxvis.

Mengelola percakapan, memutuskan kapan harus memanggil tool, dan mengembalikan
jawaban final ke user. Ini adalah implementasi "agent loop" standar:

    user message -> LLM -> (mau pakai tool? -> eksekusi tool -> kasih hasil ke LLM) -> ulangi
                         -> (tidak perlu tool) -> jawaban final ke user

KONFIRMASI AKSI SENSITIF:
Tool yang ada di TOOLS_REQUIRING_CONFIRMATION (lihat config.py) tidak langsung dieksekusi.
Sebaliknya, agent akan "menahan" pemanggilan tool tersebut dan meminta konfirmasi user lewat
callback on_confirmation_needed. Eksekusi hanya lanjut kalau user mengonfirmasi "ya".
"""

import json
import logging
import os
import time
from typing import Optional

from config import SYSTEM_PROMPT, MAX_TOOL_ITERATIONS, TOOLS_REQUIRING_CONFIRMATION, BASE_DIR
from core.llm_client import chat, OllamaError
from core.memory import load_memory, save_memory
from tools.registry import TOOL_DEFINITIONS, execute_tool

# ── Logging ───────────────────────────────────────────────────────────
# Mencatat setiap tool call (nama, argumen, hasil) dan setiap jawaban final
# model ke file log, supaya kasus "model bilang berhasil padahal tool tidak
# pernah dipanggil / gagal" bisa ditelusuri persis, bukan sekadar diduga-duga.
# File log ada di root project, misal: /home/ferxan/Downloads/ferxvis/ferxvis/ferxvis.log
_LOG_PATH = os.path.join(BASE_DIR, "ferxvis.log")
logger = logging.getLogger("ferxvis.agent")
if not logger.handlers:
    logger.setLevel(logging.DEBUG)
    _handler = logging.FileHandler(_LOG_PATH, encoding="utf-8", delay=False)
    _handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_handler)
    logger.propagate = False

    # Pastikan setiap baris log langsung ditulis ke disk (bukan menunggu buffer
    # penuh atau proses berakhir), supaya file log bisa dicek kapan saja saat
    # aplikasi masih berjalan, termasuk untuk debugging langsung oleh user.
    _orig_emit = _handler.emit
    def _emit_and_flush(record):
        _orig_emit(record)
        _handler.flush()
    _handler.emit = _emit_and_flush


class PendingConfirmation:
    """Menyimpan satu tool call yang sedang menunggu konfirmasi user."""

    def __init__(self, tool_name: str, arguments: dict):
        self.tool_name = tool_name
        self.arguments = arguments


class FerxvisAgent:
    def __init__(self, restore_memory: bool = True):
        if restore_memory:
            saved = load_memory()
            self.history = saved if saved else [{"role": "system", "content": SYSTEM_PROMPT}]
        else:
            self.history = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Saat tool sensitif dipanggil, kita simpan di sini sambil menunggu konfirmasi user.
        # Selama ini tidak None, agent dalam status "menunggu jawaban ya/tidak".
        self._pending_confirmation: Optional[PendingConfirmation] = None
        self._pending_tool_call_raw: dict | None = None  # untuk disimpan balik ke history kalau dikonfirmasi

    def reset(self):
        """Mulai percakapan baru, hapus semua histori (termasuk yang tersimpan di memory)."""
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._pending_confirmation = None
        self._pending_tool_call_raw = None
        save_memory(self.history)

    @property
    def awaiting_confirmation(self) -> bool:
        return self._pending_confirmation is not None

    def confirmation_prompt_text(self) -> str:
        """Teks yang ditampilkan ke user saat meminta konfirmasi."""
        if not self._pending_confirmation:
            return ""
        name = self._pending_confirmation.tool_name
        args = self._pending_confirmation.arguments
        readable = ", ".join(f"{k}={v}" for k, v in args.items())
        action_desc = {
            "delete_file": f"menghapus '{args.get('relative_path', '?')}'",
            "send_email": f"mengirim email ke {args.get('to', '?')} dengan subjek '{args.get('subject', '?')}'",
            "send_whatsapp_message": f"mengirim pesan WhatsApp ke {args.get('to', '?')}",
        }.get(name, f"menjalankan {name}({readable})")
        return f"⚠️ Ferxvis ingin {action_desc}. Lanjutkan? (ya/tidak)"

    def resolve_confirmation(self, user_said_yes: bool, on_tool_call=None) -> str:
        """
        Dipanggil saat user merespons prompt konfirmasi (bukan pesan biasa).
        Mengeksekusi (atau membatalkan) tool yang tertunda, lalu lanjutkan agent loop seperti biasa.
        """
        if not self._pending_confirmation:
            return "Tidak ada aksi yang menunggu konfirmasi."

        tool_name = self._pending_confirmation.tool_name
        arguments = self._pending_confirmation.arguments
        self._pending_confirmation = None
        self._pending_tool_call_raw = None

        if not user_said_yes:
            result = "Dibatalkan oleh user. Aksi tidak dijalankan."
            if on_tool_call:
                on_tool_call(tool_name, arguments, result)
            self.history.append({"role": "tool", "tool_call_id": f"call_{tool_name}", "content": result})
            return self._continue_loop(on_tool_call=on_tool_call)

        result = execute_tool(tool_name, arguments)
        if on_tool_call:
            on_tool_call(tool_name, arguments, result)
        self.history.append({"role": "tool", "tool_call_id": f"call_{tool_name}", "content": result})
        return self._continue_loop(on_tool_call=on_tool_call)

    def send(self, user_message: str, on_tool_call=None) -> str:
        """
        Kirim pesan user ke agent, jalankan loop tool-calling kalau perlu,
        dan kembalikan jawaban final sebagai string.

        Kalau ada tool sensitif yang perlu dikonfirmasi, fungsi ini akan berhenti
        dan mengembalikan teks konfirmasi (cek awaiting_confirmation == True setelah panggil ini).

        on_tool_call: callback opsional dipanggil setiap kali tool dieksekusi,
                      signature: on_tool_call(tool_name: str, arguments: dict, result: str)
        """
        self.history.append({"role": "user", "content": user_message})
        return self._continue_loop(on_tool_call=on_tool_call)

    def _continue_loop(self, on_tool_call=None) -> str:
        """Loop inti tool-calling. Dipanggil dari send() maupun resolve_confirmation()."""
        # Tool result ERROR paling akhir yang belum "dibahas" secara eksplisit oleh
        # model di jawabannya. Dipakai sebagai jaring pengaman: qwen2.5:7b adalah
        # model kecil dan kadang mengabaikan instruksi di system prompt soal wajib
        # melaporkan kegagalan. Kalau model tetap menjawab seolah semua sukses
        # padahal tool terakhir gagal, kita sisipkan koreksi otomatis di sini,
        # supaya user tidak dibohongi walau modelnya "lupa" instruksinya sendiri.
        last_unreported_error: str | None = None

        for _ in range(MAX_TOOL_ITERATIONS):
            try:
                time.sleep(3)  # Hindari rate limit Groq
                response = chat(self.history, tools=TOOL_DEFINITIONS)
            except OllamaError as e:
                logger.error(f"OllamaError: {e}")
                return f"⚠️ {e}"

            message = response.get("message", {})
            tool_calls = message.get("tool_calls")

            if not tool_calls:
                final_text = (message.get("content") or "").strip()
                # PENTING untuk debugging: log kasus di mana model TIDAK memanggil
                # tool sama sekali, tapi jawabannya "terdengar" seperti melakukan
                # sesuatu (mengandung kata kerja aksi). Ini menangkap persis kasus
                # "model berimajinasi sudah memanggil tool padahal tidak pernah".
                sounds_like_action = any(
                    kw in final_text.lower()
                    for kw in ("berhasil", "telah dibuat", "sudah dibuat", "telah dipindah", "telah dihapus")
                )
                if sounds_like_action:
                    last_user_msg = next(
                        (m.get("content", "") for m in reversed(self.history) if m.get("role") == "user"),
                        "?",
                    )
                    logger.warning(
                        f"MODEL MENGKLAIM AKSI TANPA TOOL CALL. "
                        f"User message terakhir: {last_user_msg[:200]!r}. "
                        f"Jawaban model: {final_text[:300]!r}"
                    )
                    # Ini kasus PALING berbahaya untuk user: model menulis kalimat
                    # seperti "telah dibuat" / "berhasil dipindah" padahal TIDAK
                    # PERNAH memanggil tool sama sekali (jadi tidak ada eksekusi
                    # nyata apapun di filesystem). Diam-diam mencatat ke log saja
                    # tidak cukup karena user tidak akan pernah membaca file log
                    # itu di tengah percakapan biasa. Peringatan ini WAJIB tampil
                    # di chat, bukan cuma di file log.
                    final_text = (
                        f"{final_text}\n\n"
                        f"⚠️ Catatan otomatis: jawaban di atas TIDAK disertai eksekusi tool apapun "
                        f"(tidak ada perintah yang benar-benar dijalankan ke file/folder). Kemungkinan "
                        f"besar aksi ini BELUM benar-benar terjadi, meski kalimatnya terdengar seperti "
                        f"sudah selesai. Coba minta lagi dengan kalimat yang lebih spesifik, atau cek "
                        f"langsung pakai 'lihat isi folder Documents' untuk memastikan."
                    )
                else:
                    logger.info(f"Jawaban final tanpa tool call: {final_text[:200]!r}")

                if last_unreported_error and not self._mentions_failure(final_text):
                    final_text = (
                        f"{final_text}\n\n"
                        f"⚠️ Catatan otomatis: salah satu aksi terakhir sebenarnya GAGAL "
                        f"({last_unreported_error}), meski jawaban di atas mungkin terdengar "
                        f"seperti berhasil. Mohon cek ulang sebelum dianggap selesai."
                    )

                self.history.append({"role": "assistant", "content": final_text})
                save_memory(self.history)
                return final_text

            # Normalisasi tool_calls: pastikan arguments string + type terisi
            for call in tool_calls:
                func = call.get("function", {})
                if isinstance(func.get("arguments"), dict):
                    func["arguments"] = json.dumps(func["arguments"])
                if "type" not in call:
                    call["type"] = "function"
                if "id" not in call or not call["id"]:
                    call["id"] = f"call_{func.get("name", "tool")}"
            self.history.append(message)

            for call in tool_calls:
                func_info = call.get("function", {})
                tool_name = func_info.get("name", "")
                raw_args = func_info.get("arguments", {})

                if isinstance(raw_args, str):
                    try:
                        raw_args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        raw_args = {}

                if tool_name in TOOLS_REQUIRING_CONFIRMATION:
                    # Tahan eksekusi, minta konfirmasi user dulu.
                    logger.info(f"TOOL CALL (menunggu konfirmasi): {tool_name}({raw_args})")
                    self._pending_confirmation = PendingConfirmation(tool_name, raw_args)
                    save_memory(self.history)
                    return self.confirmation_prompt_text()

                result = execute_tool(tool_name, raw_args)
                logger.info(f"TOOL CALL: {tool_name}({raw_args}) -> {result[:300] if isinstance(result, str) else result!r}")

                if on_tool_call:
                    on_tool_call(tool_name, raw_args, result)

                if isinstance(result, str) and result.startswith("ERROR"):
                    last_unreported_error = result
                else:
                    last_unreported_error = None

                tool_call_id = call.get("id") or f"call_{tool_name}"
                self.history.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": result,
                })

        save_memory(self.history)
        return ("⚠️ Maaf, prosesnya jadi terlalu panjang (terlalu banyak langkah berturut-turut). "
                "Coba pecah permintaanmu jadi beberapa instruksi yang lebih sederhana.")

    @staticmethod
    def _mentions_failure(text: str) -> bool:
        """
        Heuristik sederhana: apakah jawaban model sudah menyinggung kegagalan?
        Dipakai untuk menghindari duplikasi peringatan kalau model SUDAH benar
        melaporkan errornya sendiri sesuai instruksi system prompt.
        """
        lowered = text.lower()
        failure_keywords = (
            "gagal", "error", "tidak berhasil", "tidak bisa", "nggak bisa",
            "ga bisa", "gabisa", "ditolak", "tidak ditemukan", "maaf",
        )
        return any(keyword in lowered for keyword in failure_keywords)

