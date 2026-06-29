"""
Agent Core Ferxvis - support gambar via image_data.
"""

import json
import base64
from typing import Optional

from config import SYSTEM_PROMPT, MAX_TOOL_ITERATIONS, TOOLS_REQUIRING_CONFIRMATION
from core.llm_client import chat, OllamaError, get_active_mode
from core.memory import load_memory, save_memory
from tools.registry import TOOL_DEFINITIONS, execute_tool


# Prefix yang dipakai tools/*.py untuk menandai hasil gagal (lihat email_tools.py,
# whatsapp_tools.py, dll — semua mengembalikan string "ERROR ..." / "❌ ..." / "GAGAL ..."
# alih-alih melempar exception, supaya agent tidak crash). Karena ini cuma STRING biasa,
# tanpa pengecekan eksplisit LLM bisa lalai menganggap tool tersebut "berhasil" dan lanjut
# memakai hasilnya sebagai data asli (termasuk placeholder yang gak pernah ke-isi).
_ERROR_PREFIXES = ("ERROR", "❌", "GAGAL", "⚠️ TIDAK BISA DIPASTIKAN")


def _is_error_result(result: str) -> bool:
    """Deteksi apakah hasil tool menandakan kegagalan, bukan hasil asli."""
    if not isinstance(result, str):
        return False
    stripped = result.strip()
    return any(stripped.startswith(p) for p in _ERROR_PREFIXES)


def _wrap_tool_result_for_history(result: str) -> str:
    """Kalau hasil tool adalah error, tambahkan instruksi tegas ke LLM supaya
    tidak melanjutkan seolah-olah data tersedia (mis. menulis placeholder
    literal ke file lalu mengklaim 'berhasil disalin')."""
    if _is_error_result(result):
        return (
            f"{result}\n\n"
            "[INSTRUKSI SISTEM: Tool di atas GAGAL — hasilnya bukan data asli, "
            "jangan dipakai sebagai input untuk tool lain (jangan substitusi ke "
            "placeholder, jangan tulis ke file, jangan kirim ke kontak lain). "
            "Beritahu user secara jujur bahwa langkah ini gagal dan sebutkan "
            "alasannya dari pesan error di atas. JANGAN mengklaim berhasil.]"
        )
    return result


class PendingConfirmation:
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
        self._pending_confirmation: Optional[PendingConfirmation] = None

    def reset(self):
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._pending_confirmation = None
        save_memory(self.history)

    def load_history(self, messages: list):
        """Load chat history dari file."""
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in messages:
            if m.get("role") in ("user", "assistant") and m.get("content"):
                self.history.append(m)
        self._pending_confirmation = None

    @property
    def awaiting_confirmation(self) -> bool:
        return self._pending_confirmation is not None

    def confirmation_prompt_text(self) -> str:
        if not self._pending_confirmation:
            return ""
        name = self._pending_confirmation.tool_name
        args = self._pending_confirmation.arguments
        action_desc = {
            "delete_file": f"menghapus '{args.get('relative_path', '?')}'",
            "send_email": f"mengirim email ke {args.get('to', '?')} subjek '{args.get('subject', '?')}'",
            "send_whatsapp_message": f"mengirim WhatsApp ke {args.get('to', '?')}",
        }.get(name, f"menjalankan {name}")
        return f"⚠️ Ferxvis ingin {action_desc}. Lanjutkan?"

    def resolve_confirmation(self, user_said_yes: bool, on_tool_call=None) -> str:
        if not self._pending_confirmation:
            return "Tidak ada aksi yang menunggu konfirmasi."
        tool_name = self._pending_confirmation.tool_name
        arguments = self._pending_confirmation.arguments
        self._pending_confirmation = None

        if not user_said_yes:
            result = "Dibatalkan oleh user."
            self.history.append({"role": "tool", "content": result})
            return self._continue_loop(on_tool_call=on_tool_call)

        result = execute_tool(tool_name, arguments)
        if on_tool_call:
            on_tool_call(tool_name, arguments, result)
        self.history.append({"role": "tool", "content": _wrap_tool_result_for_history(result)})
        return self._continue_loop(on_tool_call=on_tool_call)

    def send(self, user_message: str, on_tool_call=None, image_data: dict = None) -> str:
        self.history.append({"role": "user", "content": user_message})
        self._pending_image = image_data
        return self._continue_loop(on_tool_call=on_tool_call)

    def _continue_loop(self, on_tool_call=None) -> str:
        image_data = getattr(self, "_pending_image", None)
        self._pending_image = None

        for _ in range(MAX_TOOL_ITERATIONS):
            try:
                response = chat(self.history, tools=TOOL_DEFINITIONS, image_data=image_data)
                image_data = None  # hanya kirim gambar sekali
            except OllamaError as e:
                return f"⚠️ {e}"

            message = response.get("message", {})
            tool_calls = message.get("tool_calls")

            if not tool_calls:
                final_text = message.get("content", "").strip()
                self.history.append({"role": "assistant", "content": final_text})
                save_memory(self.history)
                return final_text

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
                    self._pending_confirmation = PendingConfirmation(tool_name, raw_args)
                    save_memory(self.history)
                    return self.confirmation_prompt_text()

                result = execute_tool(tool_name, raw_args)
                if on_tool_call:
                    on_tool_call(tool_name, raw_args, result)
                self.history.append({"role": "tool", "content": _wrap_tool_result_for_history(result)})

        save_memory(self.history)
        return "⚠️ Proses terlalu panjang. Coba pecah permintaan jadi lebih sederhana."
