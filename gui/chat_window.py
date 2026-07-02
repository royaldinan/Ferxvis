"""
GUI Ferxvis v3 - Premium Dark Theme
Fitur: Chat History, Clipboard Manager, Voice Input, Saved Chats, Premium UI
Kompatibel dengan repo asli royaldinan/Ferxvis
"""

import threading
import json
import os
import io
import base64
import datetime
from pathlib import Path

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    from PIL import ImageGrab, Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

from core.agent import FerxvisAgent
from core.llm_client import check_ollama_running, check_model_available
from config import AGENT_NAME, MODEL_NAME, WORKSPACE_DIR

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Warna Premium ──────────────────────────────────────────────
BG          = "#0d1117"
SIDEBAR_BG  = "#161b22"
PANEL       = "#1c2128"
BORDER      = "#30363d"
ACCENT      = "#388bfd"
ACCENT2     = "#7c5cbf"
USER_BG     = "#1f3a5f"
AI_BG       = "#1c2128"
TOOL_BG     = "#0f2a1a"
WARN_BG     = "#2d1f00"
TEXT        = "#e6edf3"
MUTED       = "#7d8590"
GREEN       = "#3fb950"
RED         = "#f85149"
ORANGE      = "#d29922"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_CHATS_DIR = os.path.join(BASE_DIR, "saved_chats")
CLIPBOARD_FILE  = os.path.join(BASE_DIR, "clipboard_saved.json")
os.makedirs(SAVED_CHATS_DIR, exist_ok=True)


# ── Helper: load/save clipboard permanen ──────────────────────
def load_saved_clipboard():
    try:
        if os.path.exists(CLIPBOARD_FILE):
            with open(CLIPBOARD_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def save_clipboard_to_disk(items):
    try:
        with open(CLIPBOARD_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ── Saved Chats Helper ────────────────────────────────────────
def list_saved_chats():
    chats = []
    try:
        for f in sorted(Path(SAVED_CHATS_DIR).glob("*.json"), reverse=True):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                chats.append({
                    "path": str(f),
                    "title": data.get("title", f.stem),
                    "date": data.get("date", ""),
                    "messages": data.get("messages", []),
                })
            except Exception:
                pass
    except Exception:
        pass
    return chats


def save_chat_to_disk(messages, title=None):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if not title:
        user_msgs = [m for m in messages if m.get("role") == "user"]
        title = user_msgs[0]["content"][:40] if user_msgs else "Chat"
    safe = "".join(c for c in title if c.isalnum() or c in " _-")[:40].strip()
    path = os.path.join(SAVED_CHATS_DIR, f"{ts}_{safe}.json")
    exportable = [m for m in messages if m.get("role") in ("user", "assistant") and m.get("content")]
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "title": title,
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "messages": exportable,
        }, f, ensure_ascii=False, indent=2)
    return path


# ── Panel: Saved Chats ────────────────────────────────────────
class SavedChatsPanel(ctk.CTkToplevel):
    def __init__(self, parent, on_load):
        super().__init__(parent)
        self.title("Riwayat Chat")
        self.geometry("500x580")
        self.configure(fg_color=BG)
        self.on_load = on_load
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="🕐  Riwayat Chat Tersimpan",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).pack(padx=20, pady=(20, 12))

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=PANEL, corner_radius=10)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self._refresh()

    def _refresh(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        chats = list_saved_chats()
        if not chats:
            ctk.CTkLabel(self.scroll, text="Belum ada chat tersimpan.",
                         text_color=MUTED).pack(pady=20)
            return
        for chat in chats:
            row = ctk.CTkFrame(self.scroll, fg_color=BORDER, corner_radius=8)
            row.pack(fill="x", pady=3, padx=6)
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="both", expand=True, padx=10, pady=8)
            ctk.CTkLabel(info, text=chat["title"],
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=TEXT, anchor="w").pack(fill="x")
            ctk.CTkLabel(info, text=f"{chat['date']} · {len(chat['messages'])} pesan",
                         font=ctk.CTkFont(size=11), text_color=MUTED, anchor="w").pack(fill="x")
            p = chat["path"]
            m = chat["messages"]
            btns = ctk.CTkFrame(row, fg_color="transparent")
            btns.pack(side="right", padx=8)
            ctk.CTkButton(btns, text="Buka", width=60, height=28,
                          fg_color=ACCENT, hover_color="#2d75d4",
                          command=lambda msgs=m: self._load(msgs)).pack(side="left", padx=2)
            ctk.CTkButton(btns, text="Hapus", width=60, height=28,
                          fg_color=RED, hover_color="#c04040",
                          command=lambda fp=p: self._delete(fp)).pack(side="left", padx=2)

    def _load(self, messages):
        self.on_load(messages)
        self.destroy()

    def _delete(self, path):
        try:
            os.remove(path)
        except Exception:
            pass
        self._refresh()


# ── Panel: Clipboard Manager ──────────────────────────────────
class ClipboardPanel(ctk.CTkToplevel):
    def __init__(self, parent, on_paste):
        super().__init__(parent)
        self.title("Clipboard Manager")
        self.geometry("460x540")
        self.configure(fg_color=BG)
        self.on_paste = on_paste
        self.session_items = []
        self.saved_items = load_saved_clipboard()
        self._last_clip = ""
        self._build()
        self._monitor()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(16, 4))
        ctk.CTkLabel(top, text="📋  Clipboard Manager",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT).pack(side="left")
        ctk.CTkButton(top, text="Hapus Semua", width=100, height=28,
                      fg_color=RED, hover_color="#c04040",
                      command=self._clear_session).pack(side="right")

        # Tab session vs saved
        self.tab = ctk.CTkTabview(self, fg_color=PANEL)
        self.tab.pack(fill="both", expand=True, padx=16, pady=8)
        self.tab.add("Session")
        self.tab.add("Tersimpan")

        self.session_scroll = ctk.CTkScrollableFrame(self.tab.tab("Session"), fg_color="transparent")
        self.session_scroll.pack(fill="both", expand=True)

        self.saved_scroll = ctk.CTkScrollableFrame(self.tab.tab("Tersimpan"), fg_color="transparent")
        self.saved_scroll.pack(fill="both", expand=True)

        self._refresh_session()
        self._refresh_saved()

    def _monitor(self):
        try:
            import pyperclip
            current = pyperclip.paste()
            if current and current != self._last_clip and len(current.strip()) > 0:
                self._last_clip = current
                if not any(i["text"] == current for i in self.session_items):
                    self.session_items.insert(0, {"text": current, "time": datetime.datetime.now().strftime("%H:%M:%S")})
                    if len(self.session_items) > 30:
                        self.session_items = self.session_items[:30]
                    self._refresh_session()
        except Exception:
            pass
        if self.winfo_exists():
            self.after(1000, self._monitor)

    def _refresh_session(self):
        for w in self.session_scroll.winfo_children():
            w.destroy()
        if not self.session_items:
            ctk.CTkLabel(self.session_scroll, text="Belum ada clipboard.", text_color=MUTED).pack(pady=12)
            return
        for item in self.session_items:
            self._render_item(self.session_scroll, item, saved=False)

    def _refresh_saved(self):
        for w in self.saved_scroll.winfo_children():
            w.destroy()
        if not self.saved_items:
            ctk.CTkLabel(self.saved_scroll, text="Belum ada clipboard tersimpan.", text_color=MUTED).pack(pady=12)
            return
        for item in self.saved_items:
            self._render_item(self.saved_scroll, item, saved=True)

    def _render_item(self, parent, item, saved):
        row = ctk.CTkFrame(parent, fg_color=BORDER, corner_radius=8)
        row.pack(fill="x", pady=3, padx=4)
        preview = item["text"][:100].replace("\n", " ")
        ctk.CTkLabel(row, text=preview, font=ctk.CTkFont(size=12),
                     text_color=TEXT, anchor="w", wraplength=280,
                     justify="left").pack(side="left", padx=10, pady=6, fill="both", expand=True)
        btns = ctk.CTkFrame(row, fg_color="transparent")
        btns.pack(side="right", padx=6, pady=4)
        t = item["text"]
        ctk.CTkButton(btns, text="Kirim", width=52, height=24,
                      fg_color=ACCENT, hover_color="#2d75d4",
                      command=lambda txt=t: self.on_paste(txt)).pack(pady=1)
        ctk.CTkButton(btns, text="Copy", width=52, height=24,
                      fg_color=PANEL, hover_color=BORDER,
                      command=lambda txt=t: self._copy(txt)).pack(pady=1)
        if not saved:
            ctk.CTkButton(btns, text="Simpan", width=52, height=24,
                          fg_color=ACCENT2, hover_color="#6b4aad",
                          command=lambda i=item: self._save_item(i)).pack(pady=1)
        else:
            ctk.CTkButton(btns, text="Hapus", width=52, height=24,
                          fg_color=RED, hover_color="#c04040",
                          command=lambda i=item: self._delete_saved(i)).pack(pady=1)

    def _copy(self, text):
        try:
            import pyperclip
            pyperclip.copy(text)
        except Exception:
            pass

    def _save_item(self, item):
        if not any(i["text"] == item["text"] for i in self.saved_items):
            self.saved_items.insert(0, item)
            save_clipboard_to_disk(self.saved_items)
            self._refresh_saved()

    def _delete_saved(self, item):
        self.saved_items = [i for i in self.saved_items if i["text"] != item["text"]]
        save_clipboard_to_disk(self.saved_items)
        self._refresh_saved()

    def _clear_session(self):
        self.session_items = []
        self._refresh_session()


# ── Bubble Widget ─────────────────────────────────────────────
def _estimate_wrapped_lines(text: str, wrap_chars: int = 78) -> int:
    """
    Perkiraan jumlah baris setelah word-wrap, untuk menentukan tinggi CTkTextbox.
    Tidak perlu presisi sempurna (textbox tetap bisa di-scroll kalau meleset),
    cukup dekat supaya bubble tidak terlalu pendek (teks terpotong) atau
    terlalu tinggi (banyak area kosong di bawah).
    """
    total = 0
    for line in (text or "").split("\n"):
        total += max(1, -(-len(line) // wrap_chars))  # ceil division
    return max(1, total)


class Bubble(ctk.CTkFrame):
    def __init__(self, parent, role, text, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        colors = {"user": USER_BG, "assistant": AI_BG, "tool": TOOL_BG, "system": WARN_BG, "confirmation": WARN_BG}
        bg = colors.get(role, AI_BG)
        anchor = "e" if role == "user" else "w"
        icons = {"user": "👤", "assistant": "⚡", "tool": "🔧", "system": "ℹ️"}
        icon = icons.get(role, "")
        label_text = f"{icon}  {text}" if icon else text
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="x", pady=2)

        n_lines = _estimate_wrapped_lines(label_text)
        line_height_px = 20  # kira-kira, mengikuti font size=13 + padding baris
        height = min(max(n_lines * line_height_px + 20, 40), 500)  # clamp, textbox bisa di-scroll kalau lebih panjang

        # CTkTextbox dipakai (bukan CTkLabel) supaya teks bisa di-select dan
        # di-copy oleh user — CTkLabel murni display, tidak punya text
        # selection sama sekali. state="normal" tetap dipakai (bukan
        # "disabled") supaya selection & Ctrl+C jalan normal di Tk;
        # pengeditan dicegah lewat binding key/paste di bawah, bukan lewat
        # men-disable widget-nya.
        self.textbox = ctk.CTkTextbox(
            container, wrap="word", fg_color=bg, corner_radius=12,
            border_width=0, padx=14, pady=10,
            font=ctk.CTkFont(size=13), text_color=TEXT,
            height=height, activate_scrollbars=False,
        )
        self.textbox.insert("1.0", label_text)
        self._make_readonly(self.textbox)
        self.textbox.pack(anchor=anchor, padx=12, fill="x" if False else "none")

        # Lebar mengikuti proporsi window, meniru wraplength=600 versi lama.
        self.textbox.configure(width=min(620, max(200, int(len(max(label_text.split(chr(10)), key=len, default="")) * 7.2))))

    @staticmethod
    def _make_readonly(textbox: ctk.CTkTextbox):
        """
        Cegah user mengetik/menghapus isi bubble, TANPA mematikan
        kemampuan select & copy (yang akan hilang kalau pakai
        state="disabled" di beberapa versi CTkTextbox/Tk).
        """
        def _block_edit(event):
            # Izinkan kombinasi copy & select-all, blok semua input lain
            # yang bisa mengubah isi (ketik huruf, Delete, Backspace, paste, dst).
            ctrl = (event.state & 0x4) != 0  # bitmask Control di X11/Tk
            if ctrl and event.keysym.lower() in ("c", "a"):
                return None  # biarkan lewat (copy / select-all)
            return "break"  # blok semua tombol lain

        textbox.bind("<Key>", _block_edit)
        textbox.bind("<<Paste>>", lambda e: "break")
        textbox.bind("<Control-a>", lambda e: (textbox._textbox.tag_add("sel", "1.0", "end"), "break"))
        textbox.bind("<Control-A>", lambda e: (textbox._textbox.tag_add("sel", "1.0", "end"), "break"))


# ── Main Window ───────────────────────────────────────────────
class ChatWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{AGENT_NAME} — Asisten AI Personal")
        self.geometry("1060x700")
        self.minsize(780, 540)
        self.configure(fg_color=BG)

        self.agent = FerxvisAgent(restore_memory=True)
        self._confirm_frame = None
        self._pending_image = None
        self._clipboard_win = None

        self._build()
        self._check_startup()
        self._replay_history()

    def _build(self):
        root = ctk.CTkFrame(self, fg_color="transparent")
        root.pack(fill="both", expand=True)

        # ── Sidebar ──
        sb = ctk.CTkFrame(root, width=210, fg_color=SIDEBAR_BG, corner_radius=0)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        logo = ctk.CTkFrame(sb, fg_color="transparent")
        logo.pack(fill="x", padx=14, pady=(18, 6))
        ctk.CTkLabel(logo, text="⚡", font=ctk.CTkFont(size=26)).pack(side="left")
        ctk.CTkLabel(logo, text="Ferxvis", font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT).pack(side="left", padx=8)

        ctk.CTkFrame(sb, height=1, fg_color=BORDER).pack(fill="x", padx=10, pady=6)

        nav = [
            ("💬  Chat Baru", self._new_chat, ACCENT),
            ("🕐  Riwayat Chat", self._show_history, None),
            ("📋  Clipboard", self._show_clipboard, None),
        ]
        for label, cmd, color in nav:
            ctk.CTkButton(sb, text=label, anchor="w", height=38,
                          fg_color=color or "transparent", hover_color=PANEL,
                          text_color=TEXT, font=ctk.CTkFont(size=13),
                          corner_radius=8, command=cmd).pack(fill="x", padx=10, pady=2)

        ctk.CTkFrame(sb, fg_color="transparent").pack(fill="both", expand=True)
        self.mode_lbl = ctk.CTkLabel(sb, text="", font=ctk.CTkFont(size=11), text_color=MUTED)
        self.mode_lbl.pack(padx=14, pady=2)
        self.status_lbl = ctk.CTkLabel(sb, text="Mengecek...", font=ctk.CTkFont(size=11), text_color=MUTED)
        self.status_lbl.pack(padx=14)
        ctk.CTkLabel(sb, text="Ferdinand Manurung", font=ctk.CTkFont(size=10), text_color=MUTED).pack(padx=14, pady=(8, 2))
        ctk.CTkLabel(sb, text="Ferxvis v3.0", font=ctk.CTkFont(size=10), text_color=BORDER).pack(padx=14, pady=(0, 12))

        # ── Right panel ──
        right = ctk.CTkFrame(root, fg_color=BG, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        # Topbar
        topbar = ctk.CTkFrame(right, height=50, fg_color=PANEL, corner_radius=0)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)
        ctk.CTkLabel(topbar, text=f"⚡ {AGENT_NAME}",
                     font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXT).pack(side="left", padx=18)
        tbr = ctk.CTkFrame(topbar, fg_color="transparent")
        tbr.pack(side="right", padx=10)
        for lbl, cmd in [("💾 Simpan Chat", self._save_chat),
                          ("🖼️ Kirim Gambar", self._attach_image),
                          ("🎤 Suara", self._voice_input)]:
            ctk.CTkButton(tbr, text=lbl, width=110 if lbl != "🎤 Suara" else 80,
                          height=30, fg_color="transparent",
                          border_width=1, border_color=BORDER,
                          hover_color=PANEL, text_color=TEXT,
                          command=cmd).pack(side="left", padx=3)

        ctk.CTkFrame(right, height=1, fg_color=BORDER).pack(fill="x")

        # Chat area
        self.chat_area = ctk.CTkScrollableFrame(right, fg_color=BG)
        self.chat_area.pack(fill="both", expand=True)

        # Image preview bar (hidden)
        self.img_bar = ctk.CTkFrame(right, fg_color=PANEL, height=52)

        # Input bar
        inbar = ctk.CTkFrame(right, fg_color=PANEL, corner_radius=0)
        inbar.pack(fill="x", side="bottom")
        ctk.CTkFrame(inbar, height=1, fg_color=BORDER).pack(fill="x")
        inrow = ctk.CTkFrame(inbar, fg_color="transparent")
        inrow.pack(fill="x", padx=14, pady=10)
        self.input_box = ctk.CTkTextbox(
            inrow, height=50, fg_color=BORDER, border_width=0,
            corner_radius=10, font=ctk.CTkFont(size=13), text_color=TEXT)
        self.input_box.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.input_box.bind("<Return>", self._on_enter)
        # Ctrl+A default Tk BUKAN select-all (di beberapa binding malah loncat
        # ke awal baris, gaya Emacs). Override eksplisit di sini supaya Ctrl+A
        # benar-benar memilih semua teks yang sedang diketik.
        self.input_box.bind(
            "<Control-a>",
            lambda e: (self.input_box._textbox.tag_add("sel", "1.0", "end"), "break")
        )
        self.input_box.bind(
            "<Control-A>",
            lambda e: (self.input_box._textbox.tag_add("sel", "1.0", "end"), "break")
        )
        # Ctrl+V: kalau isi clipboard gambar, pasang sebagai pending image
        # (sama seperti klik tombol "Kirim Gambar"). Kalau isi clipboard
        # teks biasa, _paste_image_from_clipboard mengembalikan None supaya
        # event diteruskan ke binding paste teks bawaan CTkTextbox.
        self.input_box.bind("<Control-v>", self._paste_image_from_clipboard)
        self.input_box.bind("<Control-V>", self._paste_image_from_clipboard)
        self.send_btn = ctk.CTkButton(
            inrow, text="Kirim ➤", width=90, height=50,
            fg_color=ACCENT, hover_color="#2d75d4",
            font=ctk.CTkFont(size=13, weight="bold"), corner_radius=10,
            command=self._send)
        self.send_btn.pack(side="right")

    def _check_startup(self):
        def task():
            ollama_ok = check_ollama_running()
            model_ok = check_model_available() if ollama_ok else False
            def ui():
                if False:
                    self.mode_lbl.configure(text="🌐 Groq API\n(Online, Cepat)", text_color=GREEN)
                    self.status_lbl.configure(text="🟢 Groq Aktif", text_color=GREEN)
                elif not ollama_ok:
                    self.mode_lbl.configure(text="🖥️ Ollama Lokal", text_color=ORANGE)
                    self.status_lbl.configure(text="❌ Ollama tidak jalan", text_color=RED)
                elif not model_ok:
                    self.mode_lbl.configure(text="🖥️ Ollama Lokal", text_color=ORANGE)
                    self.status_lbl.configure(text="⚠️ Model belum di-pull", text_color=ORANGE)
                else:
                    self.mode_lbl.configure(text="🖥️ Ollama Lokal", text_color=ORANGE)
                    self.status_lbl.configure(text="🟡 Ollama Aktif", text_color=ORANGE)
                if len(self.agent.history) <= 1:
                    mode_str = "Groq API (cepat)" if LLM_PROVIDER == "groq" else "Ollama Lokal"
                    self._bubble("assistant", f"Halo Ferdinand! Saya {AGENT_NAME}, asisten AI personal kamu. Mode: {mode_str}. Ada yang bisa dibantu?")
            self.after(0, ui)
        threading.Thread(target=task, daemon=True).start()

    def _replay_history(self):
        for m in self.agent.history:
            role, content = m.get("role"), m.get("content", "")
            if role in ("user", "assistant") and content:
                self._bubble(role, content)

    def _bubble(self, role, text):
        b = Bubble(self.chat_area, role=role, text=text)
        b.pack(fill="x", pady=2, padx=6)
        self.after(60, self._scroll_bottom)
        return b

    def _scroll_bottom(self):
        self.chat_area._parent_canvas.yview_moveto(1.0)

    def _on_enter(self, e):
        self._send()
        return "break"

    def _send(self):
        if self.agent.awaiting_confirmation:
            self._bubble("system", "Gunakan tombol Ya/Tidak untuk konfirmasi.")
            return
        text = self.input_box.get("1.0", "end").strip()
        if not text and not self._pending_image:
            return
        self.input_box.delete("1.0", "end")
        self._bubble("user", text or "[Gambar]")
        self._set_enabled(False)
        if self.img_bar.winfo_ismapped():
            self.img_bar.pack_forget()
        img = self._pending_image
        self._pending_image = None
        thinking = self._bubble("assistant", "💭 Sedang berpikir...")

        def task():
            def on_tool(name, args, result):
                self.after(0, lambda: self._bubble("tool", f"{name}()\n→ {str(result)[:200]}"))
            try:
                reply = self.agent.send(text, on_tool_call=on_tool)
            except Exception as e:
                reply = f"⚠️ Error: {e}"
            self.after(0, lambda: self._finish(thinking, reply))

        threading.Thread(target=task, daemon=True).start()

    def _finish(self, thinking, reply):
        thinking.destroy()
        self._bubble("assistant", reply)
        if self.agent.awaiting_confirmation:
            self._show_confirm_buttons()
        else:
            self._set_enabled(True)
        self._scroll_bottom()

    def _show_confirm_buttons(self):
        frame = ctk.CTkFrame(self.chat_area, fg_color="transparent")
        frame.pack(fill="x", pady=6, padx=20)
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(anchor="w")
        ctk.CTkButton(inner, text="✅ Ya, lanjutkan", width=140, height=36,
                      fg_color=GREEN, hover_color="#2ea043",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=lambda: self._confirm(True)).pack(side="left", padx=(0, 8))
        ctk.CTkButton(inner, text="❌ Batalkan", width=120, height=36,
                      fg_color=RED, hover_color="#c04040",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=lambda: self._confirm(False)).pack(side="left")
        self._confirm_frame = frame
        self._scroll_bottom()

    def _confirm(self, yes):
        if self._confirm_frame:
            self._confirm_frame.destroy()
            self._confirm_frame = None
        self._bubble("user", "✅ Ya" if yes else "❌ Tidak")
        thinking = self._bubble("assistant", "💭 Memproses...")
        def task():
            try:
                reply = self.agent.resolve_confirmation(yes)
            except Exception as e:
                reply = f"⚠️ Error: {e}"
            self.after(0, lambda: self._finish(thinking, reply))
        threading.Thread(target=task, daemon=True).start()

    def _set_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.input_box.configure(state=state)
        self.send_btn.configure(state=state, text="Kirim ➤" if enabled else "...")

    # ── Actions ──
    def _new_chat(self):
        self.agent.reset()
        for w in self.chat_area.winfo_children():
            w.destroy()
        self._confirm_frame = None
        self._pending_image = None
        if self.img_bar.winfo_ismapped():
            self.img_bar.pack_forget()
        self._set_enabled(True)
        self._bubble("assistant", "Percakapan baru dimulai. Ada yang bisa saya bantu?")

    def _save_chat(self):
        try:
            save_chat_to_disk(self.agent.history)
            self._bubble("system", "✅ Chat berhasil disimpan.")
        except Exception as e:
            self._bubble("system", f"❌ Gagal simpan: {e}")

    def _show_history(self):
        def on_load(messages):
            for w in self.chat_area.winfo_children():
                w.destroy()
            self.agent.history = [self.agent.history[0]] + messages
            for m in messages:
                if m.get("role") in ("user", "assistant") and m.get("content"):
                    self._bubble(m["role"], m["content"])
            self._bubble("system", "✅ Riwayat chat dimuat.")
        SavedChatsPanel(self, on_load)

    def _show_clipboard(self):
        if self._clipboard_win and self._clipboard_win.winfo_exists():
            self._clipboard_win.lift()
            return
        def on_paste(text):
            self.input_box.delete("1.0", "end")
            self.input_box.insert("1.0", text)
        self._clipboard_win = ClipboardPanel(self, on_paste)

    def _attach_image(self):
        fp = filedialog.askopenfilename(
            title="Pilih Gambar",
            filetypes=[("Image", "*.png *.jpg *.jpeg *.gif *.webp *.bmp")]
        )
        if not fp:
            return
        try:
            with open(fp, "rb") as f:
                raw = f.read()
            b64 = base64.b64encode(raw).decode("utf-8")
            ext = Path(fp).suffix.lower()
            mt = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                  ".gif": "image/gif", ".webp": "image/webp"}.get(ext, "image/jpeg")
            self._set_pending_image(b64, mt, label=Path(fp).name)
        except Exception as e:
            messagebox.showerror("Error", f"Gagal buka gambar: {e}")

    def _set_pending_image(self, b64: str, media_type: str, label: str):
        """
        Set gambar yang akan dikirim di pesan berikutnya, dan tampilkan preview
        bar-nya. Dipanggil dari dua jalur: _attach_image (pilih file lewat
        dialog OS) dan _paste_image_from_clipboard (Ctrl+V) — keduanya
        berakhir di jalur yang sama persis, supaya gambar dari clipboard
        diperlakukan identik dengan gambar dari file.
        """
        self._pending_image = {"base64": b64, "media_type": media_type}
        for w in self.img_bar.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.img_bar, text=f"🖼️ {label}",
                     font=ctk.CTkFont(size=12), text_color=TEXT).pack(side="left", padx=16)
        ctk.CTkButton(self.img_bar, text="✕", width=28, height=28,
                      fg_color="transparent", hover_color=BORDER, text_color=MUTED,
                      command=lambda: (self.img_bar.pack_forget(), setattr(self, "_pending_image", None))
                      ).pack(side="right", padx=8)
        self.img_bar.pack(fill="x", before=self.chat_area)

    def _paste_image_from_clipboard(self, event=None):
        """
        Tangani Ctrl+V: kalau isi clipboard adalah GAMBAR (bukan teks),
        pasang sebagai pending image (jalur sama dengan tombol "Kirim Gambar").
        Kalau isi clipboard teks biasa, biarkan lewat ke perilaku paste teks
        normal di textbox (return None, JANGAN "break").
        """
        if not _PIL_AVAILABLE:
            messagebox.showerror(
                "Fitur belum aktif",
                "Paste gambar butuh library Pillow. Jalankan:\n\npip install Pillow\n\n"
                "lalu restart Ferxvis."
            )
            return "break"

        try:
            clip = ImageGrab.grabclipboard()
        except Exception as e:
            # Di Linux, ImageGrab.grabclipboard() butuh xclip atau wl-clipboard
            # terpasang di OS (bukan cuma pip package). Kalau tidak ada,
            # Pillow melempar exception yang membingungkan kalau tidak
            # dijelaskan ulang di sini.
            messagebox.showerror(
                "Gagal membaca clipboard",
                f"Tidak bisa membaca gambar dari clipboard.\n\n"
                f"Di Linux, ini butuh 'xclip' (X11) atau 'wl-clipboard' (Wayland) "
                f"terpasang di sistem. Coba jalankan salah satu:\n\n"
                f"  sudo dnf install xclip\n"
                f"  sudo dnf install wl-clipboard\n\n"
                f"Detail error: {e}"
            )
            return "break"

        if clip is None:
            # Clipboard kosong ATAU isinya teks biasa (grabclipboard hanya
            # menangkap gambar/file, bukan teks). Biarkan event lanjut ke
            # binding paste teks normal milik CTkTextbox.
            return None

        # grabclipboard() bisa mengembalikan objek PIL.Image langsung
        # (screenshot / copy dari image viewer), ATAU list path file
        # (kalau user copy file gambar dari file manager).
        try:
            if isinstance(clip, list) and clip:
                fp = clip[0]
                with open(fp, "rb") as f:
                    raw = f.read()
                b64 = base64.b64encode(raw).decode("utf-8")
                ext = Path(fp).suffix.lower()
                mt = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                      ".gif": "image/gif", ".webp": "image/webp"}.get(ext, "image/jpeg")
                self._set_pending_image(b64, mt, label=Path(fp).name)
            elif isinstance(clip, Image.Image):
                buf = io.BytesIO()
                # Clipboard image biasanya tidak punya nama file / format asli
                # yang jelas (misal hasil screenshot); simpan sebagai PNG,
                # format lossless yang aman untuk segala jenis gambar.
                clip.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                self._set_pending_image(b64, "image/png", label="(gambar dari clipboard)")
            else:
                return None  # bukan gambar, biarkan lewat sebagai paste teks biasa
        except Exception as e:
            messagebox.showerror("Error", f"Gagal memproses gambar dari clipboard: {e}")

        return "break"

    def _voice_input(self):
        self.send_btn.configure(text="🔴...", state="disabled")
        def task():
            try:
                import speech_recognition as sr
                r = sr.Recognizer()
                with sr.Microphone() as src:
                    r.adjust_for_ambient_noise(src, duration=0.5)
                    audio = r.listen(src, timeout=10, phrase_time_limit=30)
                text = r.recognize_google(audio, language="id-ID")
                self.after(0, lambda: (
                    self.input_box.delete("1.0", "end"),
                    self.input_box.insert("1.0", text)
                ))
            except Exception as e:
                self.after(0, lambda: self._bubble("system", f"⚠️ Voice error: {e}"))
            finally:
                self.after(0, lambda: self.send_btn.configure(text="Kirim ➤", state="normal"))
        threading.Thread(target=task, daemon=True).start()


def run_gui():
    app = ChatWindow()
    app.mainloop()
