"""
GUI Premium Ferxvis - Dark theme, sidebar, chat history, clipboard, voice, image.
Voice: Groq Whisper API (kualitas tinggi) atau Google fallback.
Input: Ctrl+A select all, paste gambar dari clipboard.
"""

import threading
import base64
import os
import io
import json
import subprocess
import tempfile
import wave
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk

from core.agent import FerxvisAgent
from core.llm_client import check_ollama_running, check_model_available, get_active_mode, get_quota_info
from core.memory import (save_chat_history, list_chat_histories,
                         load_chat_history, delete_chat_history,
                         load_saved_clipboard, add_saved_clipboard_item,
                         delete_saved_clipboard_item, clear_saved_clipboard)
from config import AGENT_NAME, MODEL_NAME, GROQ_MODEL, GROQ_API_KEY

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Warna tema premium ─────────────────────────────────────────
C_BG        = "#0f1117"
C_SIDEBAR   = "#161b27"
C_PANEL     = "#1c2333"
C_BORDER    = "#2a3347"
C_ACCENT    = "#4f8ef7"
C_ACCENT2   = "#7c5cbf"
C_USER_BG   = "#1e3a5f"
C_AI_BG     = "#1a2235"
C_TOOL_BG   = "#162012"
C_WARN_BG   = "#2d1f00"
C_TEXT      = "#e8eaf0"
C_MUTED     = "#6b7a99"
C_GREEN     = "#22c55e"
C_RED       = "#ef4444"
C_ORANGE    = "#f97316"


# ── Groq Whisper voice recording ──────────────────────────────

def _record_audio_pyaudio(duration_max=30, silence_timeout=2.0, stop_flag=None):
    """Record audio pakai PyAudio dengan VAD (berhenti otomatis saat hening).
    stop_flag: callable opsional, kalau return True maka rekaman dihentikan segera
    (dipakai supaya window bisa ditutup paksa walau sedang merekam)."""
    import pyaudio
    import numpy as np

    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    SILENCE_THRESHOLD = 500   # RMS threshold untuk silence detection
    SILENCE_FRAMES = int(RATE / CHUNK * silence_timeout)

    pa = pyaudio.PyAudio()
    stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                     input=True, frames_per_buffer=CHUNK)

    frames = []
    silent_count = 0
    started = False

    try:
        for _ in range(0, int(RATE / CHUNK * duration_max)):
            if stop_flag is not None and stop_flag():
                break  # Window ditutup / app diminta keluar — hentikan segera

            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)

            # RMS energy
            audio_data = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))

            if rms > SILENCE_THRESHOLD:
                started = True
                silent_count = 0
            elif started:
                silent_count += 1
                if silent_count >= SILENCE_FRAMES:
                    break  # Berhenti setelah hening cukup lama
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()

    # Simpan ke file WAV sementara
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(pa.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    return tmp.name


def _transcribe_groq_whisper(audio_path: str) -> str:
    """Kirim audio ke Groq Whisper API pakai requests (bypass Cloudflare)."""
    import requests

    with open(audio_path, 'rb') as f:
        audio_data = f.read()

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }
    files = {
        "file": ("audio.wav", audio_data, "audio/wav"),
    }
    data = {
        "model": "whisper-large-v3",
        "language": "id",
        "response_format": "json",
    }

    resp = requests.post(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        headers=headers,
        files=files,
        data=data,
        timeout=30,
    )

    if not resp.ok:
        raise Exception(f"Groq Whisper error {resp.status_code}: {resp.text}")

    return resp.json().get("text", "").strip()
def _transcribe_google_fallback(audio_path: str) -> str:
    """Fallback ke Google Speech Recognition."""
    import speech_recognition as sr
    r = sr.Recognizer()
    with sr.AudioFile(audio_path) as source:
        audio = r.record(source)
    return r.recognize_google(audio, language="id-ID")


# ── Sidebar ────────────────────────────────────────────────────

class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, on_new_chat, on_show_history, on_show_clipboard,
                 on_show_saved_clipboard, **kwargs):
        super().__init__(parent, width=220, fg_color=C_SIDEBAR, corner_radius=0, **kwargs)
        self.pack_propagate(False)

        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(fill="x", padx=16, pady=(20, 8))
        ctk.CTkLabel(logo_frame, text="⚡", font=ctk.CTkFont(size=28)).pack(side="left")
        ctk.CTkLabel(logo_frame, text="Ferxvis",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=C_TEXT).pack(side="left", padx=8)

        ctk.CTkFrame(self, height=1, fg_color=C_BORDER).pack(fill="x", padx=12, pady=8)

        nav_items = [
            ("💬  Chat Baru", on_new_chat, C_ACCENT),
            ("🕐  Riwayat Chat", on_show_history, None),
            ("📋  Clipboard", on_show_clipboard, None),
            ("💾  Saved Clipboard", on_show_saved_clipboard, None),
        ]
        for label, cmd, color in nav_items:
            btn = ctk.CTkButton(
                self, text=label, anchor="w", height=40,
                fg_color=color or "transparent",
                hover_color=C_PANEL,
                text_color=C_TEXT,
                font=ctk.CTkFont(size=13),
                corner_radius=8,
                command=cmd,
            )
            btn.pack(fill="x", padx=12, pady=3)

        ctk.CTkFrame(self, height=1, fg_color=C_BORDER).pack(fill="x", padx=12, pady=8)

        self.mode_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=11),
            text_color=C_MUTED, justify="left"
        )
        self.mode_label.pack(fill="x", padx=16, pady=4)

        self.status_label = ctk.CTkLabel(
            self, text="Mengecek...", font=ctk.CTkFont(size=11),
            text_color=C_MUTED
        )
        self.status_label.pack(fill="x", padx=16)

        self.quota_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=10),
            text_color=C_MUTED, justify="left"
        )
        self.quota_label.pack(fill="x", padx=16, pady=(4, 0))

        ctk.CTkFrame(self, fg_color="transparent").pack(fill="both", expand=True)

        ctk.CTkLabel(self, text="Ferdinand Manurung",
                     font=ctk.CTkFont(size=11), text_color=C_MUTED).pack(padx=16, pady=(0, 4))
        ctk.CTkLabel(self, text="Ferxvis v2.1",
                     font=ctk.CTkFont(size=10), text_color=C_BORDER).pack(padx=16, pady=(0, 12))

    def set_status(self, text, color=None):
        self.status_label.configure(text=text, text_color=color or C_MUTED)

    def set_mode(self, mode: str):
        if mode == "groq":
            self.mode_label.configure(
                text="🌐 Groq API\n(Online, Cepat)",
                text_color=C_GREEN
            )
        else:
            self.mode_label.configure(
                text="🖥️ Ollama Lokal\n(Offline Mode)",
                text_color=C_ORANGE
            )

    def set_quota(self, remaining, limit, reset_str=None):
        """Update label sisa quota harian Groq. remaining/limit bisa None kalau belum ada data."""
        if remaining is None or limit is None:
            self.quota_label.configure(text="")
            return

        pct = (remaining / limit) if limit else 0
        if pct <= 0.1:
            color = C_RED
        elif pct <= 0.3:
            color = C_ORANGE
        else:
            color = C_MUTED

        text = f"📊 Sisa kuota: {remaining}/{limit} hari ini"
        if reset_str:
            text += f"\n⏱ Reset dalam: {reset_str}"
        self.quota_label.configure(text=text, text_color=color)


# ── Chat Bubble ────────────────────────────────────────────────

class ChatBubble(ctk.CTkFrame):
    def __init__(self, parent, role: str, text: str, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        color_map = {
            "user": C_USER_BG,
            "assistant": C_AI_BG,
            "tool": C_TOOL_BG,
            "system": C_WARN_BG,
            "confirmation": C_WARN_BG,
        }
        bg = color_map.get(role, C_AI_BG)
        anchor = "e" if role == "user" else "w"
        prefix = {"user": "👤", "assistant": "⚡", "tool": "🔧", "system": "ℹ️"}.get(role, "")

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="x", pady=2)

        bubble = ctk.CTkLabel(
            container,
            text=f"{prefix}  {text}" if prefix else text,
            justify="left",
            wraplength=580,
            fg_color=bg,
            corner_radius=12,
            padx=14, pady=10,
            font=ctk.CTkFont(size=13),
            text_color=C_TEXT,
        )
        bubble.pack(anchor=anchor, padx=12)


# ── History Panel ──────────────────────────────────────────────

class HistoryPanel(ctk.CTkToplevel):
    def __init__(self, parent, on_load_callback):
        super().__init__(parent)
        self.title("Riwayat Chat")
        self.geometry("520x600")
        self.configure(fg_color=C_BG)
        self.on_load = on_load_callback
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="🕐  Riwayat Chat",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=C_TEXT).pack(padx=20, pady=(20, 12))

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=C_PANEL, corner_radius=10)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self._load_list()

    def _load_list(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        histories = list_chat_histories()
        if not histories:
            ctk.CTkLabel(self.scroll, text="Belum ada riwayat chat.",
                         text_color=C_MUTED).pack(pady=20)
            return

        for h in histories:
            row = ctk.CTkFrame(self.scroll, fg_color=C_BORDER, corner_radius=8)
            row.pack(fill="x", pady=4, padx=8)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="both", expand=True, padx=12, pady=8)

            ctk.CTkLabel(info, text=h["title"],
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=C_TEXT, anchor="w").pack(fill="x")
            ctk.CTkLabel(info,
                         text=f"{h['message_count']} pesan  •  {h['saved_at'][:16].replace('T', ' ')}",
                         font=ctk.CTkFont(size=11), text_color=C_MUTED, anchor="w").pack(fill="x")

            btns = ctk.CTkFrame(row, fg_color="transparent")
            btns.pack(side="right", padx=8)

            fp = h["filepath"]
            ctk.CTkButton(btns, text="Buka", width=60, height=28,
                          fg_color=C_ACCENT, hover_color="#3a7be0",
                          command=lambda f=fp: self._load(f)).pack(side="left", padx=2)
            ctk.CTkButton(btns, text="Hapus", width=60, height=28,
                          fg_color=C_RED, hover_color="#cc2222",
                          command=lambda f=fp: self._delete(f)).pack(side="left", padx=2)

    def _load(self, filepath):
        msgs = load_chat_history(filepath)
        self.on_load(msgs)
        self.destroy()

    def _delete(self, filepath):
        delete_chat_history(filepath)
        self._load_list()


# ── Clipboard Panel ────────────────────────────────────────────

class ClipboardPanel(ctk.CTkToplevel):
    def __init__(self, parent, on_paste_callback):
        super().__init__(parent)
        self.title("Clipboard Manager")
        self.geometry("520x580")
        self.configure(fg_color=C_BG)
        self.on_paste = on_paste_callback
        self.items = []
        self._build()
        self._start_monitor()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 8))

        ctk.CTkLabel(header, text="📋  Clipboard",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=C_TEXT).pack(side="left")

        ctk.CTkButton(header, text="🗑 Bersihkan", width=100, height=30,
                      fg_color=C_RED, hover_color="#cc2222",
                      command=self._clear).pack(side="right")

        ctk.CTkLabel(self,
                     text="Copy sesuatu untuk menyimpannya di sini.",
                     font=ctk.CTkFont(size=11), text_color=C_MUTED).pack()

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=C_PANEL, corner_radius=10)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=12)

    def _start_monitor(self):
        self._last = ""
        self._monitor()

    def _monitor(self):
        try:
            import pyperclip
            current = pyperclip.paste()
            if current and current != self._last and len(current.strip()) > 0:
                self._last = current
                self._add_item(current)
        except Exception:
            pass
        if self.winfo_exists():
            self.after(1000, self._monitor)

    def _add_item(self, text: str):
        if any(i["text"] == text for i in self.items):
            return
        self.items.insert(0, {"text": text, "time": datetime.now().strftime("%H:%M:%S")})
        if len(self.items) > 50:
            self.items = self.items[:50]
        self._refresh_list()

    def _refresh_list(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        for item in self.items:
            row = ctk.CTkFrame(self.scroll, fg_color=C_BORDER, corner_radius=8)
            row.pack(fill="x", pady=3, padx=4)

            # Preview teks
            preview = item["text"][:100].replace("\n", " ")
            ctk.CTkLabel(
                row, text=preview,
                font=ctk.CTkFont(size=12), text_color=C_TEXT,
                anchor="w", wraplength=280, justify="left"
            ).pack(side="left", padx=10, pady=8, fill="both", expand=True)

            # Tombol-tombol di kanan
            btns = ctk.CTkFrame(row, fg_color="transparent")
            btns.pack(side="right", padx=6, pady=6)

            t = item["text"]

            ctk.CTkLabel(btns, text=item["time"],
                         font=ctk.CTkFont(size=10), text_color=C_MUTED).pack()

            btn_row = ctk.CTkFrame(btns, fg_color="transparent")
            btn_row.pack(pady=(2, 0))

            # Tombol Copy — copy ulang ke clipboard sistem
            ctk.CTkButton(
                btn_row, text="📋 Copy", width=58, height=26,
                fg_color=C_ACCENT2, hover_color="#6448a8",
                font=ctk.CTkFont(size=11),
                command=lambda txt=t: self._copy_to_clipboard(txt)
            ).pack(side="left", padx=(0, 3))

            # Tombol Simpan — simpan permanen ke Saved Clipboard (persist ke disk)
            ctk.CTkButton(
                btn_row, text="💾 Simpan", width=58, height=26,
                fg_color="transparent", border_width=1, border_color=C_BORDER,
                hover_color=C_PANEL, text_color=C_TEXT,
                font=ctk.CTkFont(size=11),
                command=lambda txt=t: self._save_permanently(txt)
            ).pack(side="left", padx=(0, 3))

            # Tombol Kirim — kirim ke input box AI
            ctk.CTkButton(
                btn_row, text="➤ Kirim", width=58, height=26,
                fg_color=C_ACCENT, hover_color="#3a7be0",
                font=ctk.CTkFont(size=11),
                command=lambda txt=t: self.on_paste(txt)
            ).pack(side="left")

    def _save_permanently(self, text: str):
        """Simpan item ini ke Saved Clipboard (persist, tidak hilang saat ditutup)."""
        added = add_saved_clipboard_item(text)
        if not added:
            messagebox.showinfo("Saved Clipboard", "Item ini sudah ada di Saved Clipboard.")

    def _copy_to_clipboard(self, text: str):
        """Copy item kembali ke clipboard sistem."""
        try:
            import pyperclip
            pyperclip.copy(text)
            # Visual feedback singkat tidak bisa di label yang berbeda thread, skip aja
        except Exception:
            pass

    def _clear(self):
        self.items = []
        self._refresh_list()


# ── Saved Clipboard Panel ──────────────────────────────────────
# Beda dari ClipboardPanel di atas: panel ini menampilkan item yang
# SUDAH disimpan secara permanen (lewat tombol "💾 Simpan" di ClipboardPanel,
# atau ditambah langsung dari sini). Data persist ke saved_clipboard.json,
# sama seperti "Simpan Chat" persist ke chat_histories/, jadi tetap ada
# walau panel ditutup atau Ferxvis dibuka ulang.

class SavedClipboardPanel(ctk.CTkToplevel):
    def __init__(self, parent, on_paste_callback):
        super().__init__(parent)
        self.title("Saved Clipboard")
        self.geometry("520x600")
        self.configure(fg_color=C_BG)
        self.on_paste = on_paste_callback
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 8))

        ctk.CTkLabel(header, text="💾  Saved Clipboard",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=C_TEXT).pack(side="left")

        ctk.CTkButton(header, text="🗑 Bersihkan Semua", width=130, height=30,
                      fg_color=C_RED, hover_color="#cc2222",
                      command=self._clear_all).pack(side="right")

        ctk.CTkLabel(self,
                     text="Item yang disimpan permanen dari Clipboard tetap ada di sini.",
                     font=ctk.CTkFont(size=11), text_color=C_MUTED).pack()

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=C_PANEL, corner_radius=10)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=12)
        self._load_list()

    def _load_list(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        items = load_saved_clipboard()
        if not items:
            ctk.CTkLabel(self.scroll, text="Belum ada item yang disimpan.",
                         text_color=C_MUTED).pack(pady=20)
            return

        for item in items:
            row = ctk.CTkFrame(self.scroll, fg_color=C_BORDER, corner_radius=8)
            row.pack(fill="x", pady=3, padx=4)

            preview = item["text"][:100].replace("\n", " ")
            ctk.CTkLabel(
                row, text=preview,
                font=ctk.CTkFont(size=12), text_color=C_TEXT,
                anchor="w", wraplength=280, justify="left"
            ).pack(side="left", padx=10, pady=8, fill="both", expand=True)

            btns = ctk.CTkFrame(row, fg_color="transparent")
            btns.pack(side="right", padx=6, pady=6)

            t = item["text"]
            saved_at = item.get("saved_at", "")

            ctk.CTkLabel(btns, text=saved_at[:16].replace("T", " "),
                         font=ctk.CTkFont(size=10), text_color=C_MUTED).pack()

            btn_row = ctk.CTkFrame(btns, fg_color="transparent")
            btn_row.pack(pady=(2, 0))

            ctk.CTkButton(
                btn_row, text="📋 Copy", width=58, height=26,
                fg_color=C_ACCENT2, hover_color="#6448a8",
                font=ctk.CTkFont(size=11),
                command=lambda txt=t: self._copy_to_clipboard(txt)
            ).pack(side="left", padx=(0, 3))

            ctk.CTkButton(
                btn_row, text="➤ Kirim", width=58, height=26,
                fg_color=C_ACCENT, hover_color="#3a7be0",
                font=ctk.CTkFont(size=11),
                command=lambda txt=t: self.on_paste(txt)
            ).pack(side="left", padx=(0, 3))

            ctk.CTkButton(
                btn_row, text="🗑", width=30, height=26,
                fg_color=C_RED, hover_color="#cc2222",
                font=ctk.CTkFont(size=11),
                command=lambda sa=saved_at: self._delete_item(sa)
            ).pack(side="left")

    def _copy_to_clipboard(self, text: str):
        try:
            import pyperclip
            pyperclip.copy(text)
        except Exception:
            pass

    def _delete_item(self, saved_at: str):
        delete_saved_clipboard_item(saved_at)
        self._load_list()

    def _clear_all(self):
        clear_saved_clipboard()
        self._load_list()


# ── Main Chat Window ───────────────────────────────────────────

class ChatWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{AGENT_NAME} — Asisten AI Personal")
        self.geometry("1100x720")
        self.minsize(800, 560)
        self.configure(fg_color=C_BG)

        self.agent = FerxvisAgent(restore_memory=True)
        self._confirmation_frame = None
        self._pending_image = None
        self._clipboard_panel = None
        self._saved_clipboard_panel = None
        self._is_recording = False
        self._is_closing = False

        self._build_ui()
        self._check_startup()
        self._replay_history()

        # Pastikan window benar-benar tertutup walau ada thread (voice/API)
        # yang masih jalan di background — tanpa ini, klik X bisa terasa
        # "tidak merespon" karena tkinter menunggu thread non-daemon/blocking.
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        """Handler saat window ditutup (klik X / Alt+F4 / close all)."""
        self._is_closing = True
        try:
            self.destroy()
        except Exception:
            pass
        # Paksa keluar proses segera. Thread voice/HTTP yang masih
        # berjalan di background (daemon) tidak akan menahan proses,
        # tapi os._exit memastikan tidak ada yang nyangkut sama sekali.
        os._exit(0)

    def _build_ui(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True)

        self.sidebar = Sidebar(
            main,
            on_new_chat=self._on_new_chat,
            on_show_history=self._on_show_history,
            on_show_clipboard=self._on_show_clipboard,
            on_show_saved_clipboard=self._on_show_saved_clipboard,
        )
        self.sidebar.pack(side="left", fill="y")

        right = ctk.CTkFrame(main, fg_color=C_BG, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        # Topbar
        topbar = ctk.CTkFrame(right, height=52, fg_color=C_PANEL, corner_radius=0)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        ctk.CTkLabel(topbar, text=f"⚡ {AGENT_NAME}",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=C_TEXT).pack(side="left", padx=20)

        btn_frame = ctk.CTkFrame(topbar, fg_color="transparent")
        btn_frame.pack(side="right", padx=12)

        ctk.CTkButton(btn_frame, text="💾 Simpan Chat", width=110, height=30,
                      fg_color="transparent", border_width=1, border_color=C_BORDER,
                      hover_color=C_PANEL, text_color=C_TEXT,
                      command=self._on_save_chat).pack(side="left", padx=4)

        ctk.CTkButton(btn_frame, text="🖼️ Kirim Gambar", width=110, height=30,
                      fg_color="transparent", border_width=1, border_color=C_BORDER,
                      hover_color=C_PANEL, text_color=C_TEXT,
                      command=self._on_attach_image).pack(side="left", padx=4)

        self.voice_btn = ctk.CTkButton(
            btn_frame, text="🎤 Suara", width=90, height=30,
            fg_color="transparent", border_width=1, border_color=C_BORDER,
            hover_color=C_PANEL, text_color=C_TEXT,
            command=self._on_voice_input
        )
        self.voice_btn.pack(side="left", padx=4)

        ctk.CTkFrame(right, height=1, fg_color=C_BORDER).pack(fill="x")

        self.chat_frame = ctk.CTkScrollableFrame(right, fg_color=C_BG, label_text="")
        self.chat_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Image preview bar (hidden)
        self.img_bar = ctk.CTkFrame(right, fg_color=C_PANEL, height=60)

        # Input area
        input_area = ctk.CTkFrame(right, fg_color=C_PANEL, corner_radius=0)
        input_area.pack(fill="x", side="bottom")

        ctk.CTkFrame(input_area, height=1, fg_color=C_BORDER).pack(fill="x")

        input_row = ctk.CTkFrame(input_area, fg_color="transparent")
        input_row.pack(fill="x", padx=16, pady=12)

        self.input_box = ctk.CTkTextbox(
            input_row, height=52, fg_color=C_BORDER,
            border_width=0, corner_radius=10,
            font=ctk.CTkFont(size=13), text_color=C_TEXT,
            scrollbar_button_color=C_BORDER,
        )
        self.input_box.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Keybinds input box
        self.input_box.bind("<Return>", self._on_enter)
        self.input_box.bind("<Shift-Return>", lambda e: None)
        self.input_box.bind("<Control-a>", self._on_ctrl_a)
        self.input_box.bind("<Control-A>", self._on_ctrl_a)
        self.input_box.bind("<Control-v>", self._on_ctrl_v)
        self.input_box.bind("<Control-V>", self._on_ctrl_v)

        self.send_btn = ctk.CTkButton(
            input_row, text="Kirim ➤", width=90, height=52,
            fg_color=C_ACCENT, hover_color="#3a7be0",
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=10,
            command=self._on_send,
        )
        self.send_btn.pack(side="right")

    # ── Startup check ──────────────────────────────────────────

    def _check_startup(self):
        def task():
            mode = get_active_mode()
            if mode == "groq":
                status = ("🟢 Groq API Aktif", C_GREEN)
                mode_str = "☁️ Groq API (cepat)"
            else:
                ollama_ok = check_ollama_running()
                model_ok = check_model_available() if ollama_ok else False
                if not ollama_ok:
                    status = ("❌ Ollama tidak jalan", C_RED)
                elif not model_ok:
                    status = ("⚠️ Model belum di-pull", C_ORANGE)
                else:
                    status = ("🟡 Ollama Lokal", C_ORANGE)
                mode_str = "🖥️ Ollama Lokal"

            def ui():
                self.sidebar.set_mode(mode)
                self.sidebar.set_status(status[0], status[1])
                if len(self.agent.history) <= 1:
                    self._add_bubble(
                        "assistant",
                        f"Halo, Ferdinand! Saya Ferxvis, asisten AI personal kamu. "
                        f"Mode aktif: {mode_str}. Ada yang bisa saya bantu hari ini?"
                    )
            self.after(0, ui)
        threading.Thread(target=task, daemon=True).start()

    def _replay_history(self):
        for msg in self.agent.history:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user" and content:
                self._add_bubble("user", content)
            elif role == "assistant" and content:
                self._add_bubble("assistant", content)

    def _add_bubble(self, role: str, text: str):
        bubble = ChatBubble(self.chat_frame, role=role, text=text)
        bubble.pack(fill="x", pady=2, padx=8)
        self.after(60, self._scroll_bottom)

    def _add_confirmation_buttons(self):
        frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        frame.pack(fill="x", pady=6, padx=20)
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(anchor="w")
        ctk.CTkButton(inner, text="✅ Ya, lanjutkan", width=140, height=36,
                      fg_color=C_GREEN, hover_color="#16a34a",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=lambda: self._on_confirm(True)).pack(side="left", padx=(0, 8))
        ctk.CTkButton(inner, text="❌ Batalkan", width=120, height=36,
                      fg_color=C_RED, hover_color="#cc2222",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=lambda: self._on_confirm(False)).pack(side="left")
        self._confirmation_frame = frame
        self.after(60, self._scroll_bottom)

    def _remove_confirmation_buttons(self):
        if self._confirmation_frame:
            self._confirmation_frame.destroy()
            self._confirmation_frame = None

    def _scroll_bottom(self):
        self.chat_frame._parent_canvas.yview_moveto(1.0)

    # ── Input keybinds ─────────────────────────────────────────

    def _on_enter(self, event):
        self._on_send()
        return "break"

    def _on_ctrl_a(self, event):
        """Ctrl+A: select all teks di input box."""
        self.input_box.tag_add("sel", "1.0", "end")
        return "break"

    def _on_ctrl_v(self, event):
        """Ctrl+V: paste teks atau gambar dari clipboard."""
        # Coba dulu gambar dari clipboard (PIL)
        try:
            from PIL import ImageGrab, Image
            img = ImageGrab.grabclipboard()
            if img is not None and hasattr(img, 'mode'):
                # Ada gambar di clipboard
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                self._pending_image = {"base64": b64, "media_type": "image/png"}

                # Tampilkan preview bar
                for w in self.img_bar.winfo_children():
                    w.destroy()
                ctk.CTkLabel(
                    self.img_bar,
                    text=f"🖼️  Gambar dari clipboard ({img.width}×{img.height})  — siap dikirim",
                    font=ctk.CTkFont(size=12), text_color=C_TEXT
                ).pack(side="left", padx=16, pady=8)
                ctk.CTkButton(
                    self.img_bar, text="✕", width=30, height=30,
                    fg_color="transparent", hover_color=C_BORDER,
                    text_color=C_MUTED, command=self._cancel_image
                ).pack(side="right", padx=8)
                self.img_bar.pack(fill="x", before=self.chat_frame)
                return "break"
        except Exception:
            pass

        # Kalau bukan gambar, biarkan Ctrl+V default paste teks
        return None

    # ── Send / confirm ─────────────────────────────────────────

    def _on_send(self):
        if self.agent.awaiting_confirmation:
            self._add_bubble("system", "Gunakan tombol Ya/Tidak untuk konfirmasi terlebih dahulu.")
            return
        text = self.input_box.get("1.0", "end").strip()
        if not text and not self._pending_image:
            return
        self.input_box.delete("1.0", "end")

        display_text = text or "[Gambar dikirim]"
        self._add_bubble("user", display_text)
        self._set_input_enabled(False)

        if self.img_bar.winfo_ismapped():
            self.img_bar.pack_forget()

        image_data = self._pending_image
        self._pending_image = None

        thinking = self._add_thinking_bubble()

        def task():
            def on_tool(name, args, result):
                self.after(0, lambda: self._add_bubble(
                    "tool", f"{name}({self._fmt(args)})\n→ {result[:200]}"
                ))
            try:
                reply = self.agent.send(text, on_tool_call=on_tool, image_data=image_data)
            except Exception as e:
                reply = f"⚠️ Error: {e}"
            self.after(0, lambda: self._finish(thinking, reply))

        threading.Thread(target=task, daemon=True).start()

    def _add_thinking_bubble(self):
        frame = ctk.CTkFrame(self.chat_frame, fg_color=C_AI_BG, corner_radius=12)
        frame.pack(anchor="w", padx=20, pady=4)
        label = ctk.CTkLabel(frame, text="⚡  Sedang berpikir...",
                             font=ctk.CTkFont(size=13), text_color=C_MUTED,
                             padx=14, pady=10)
        label.pack()
        self.after(60, self._scroll_bottom)
        return frame

    def _finish(self, thinking_widget, reply: str):
        thinking_widget.destroy()
        self._add_bubble("assistant", reply)
        self._refresh_quota_label()
        if self.agent.awaiting_confirmation:
            self._add_confirmation_buttons()
            self._set_input_enabled(False)
        else:
            self._set_input_enabled(True)
        self._scroll_bottom()

    def _refresh_quota_label(self):
        try:
            info = get_quota_info()
            self.sidebar.set_quota(
                info.get("remaining_requests"),
                info.get("limit_requests"),
                info.get("reset_requests"),
            )
        except Exception:
            pass  # quota display tidak boleh sampai bikin chat error

    def _on_confirm(self, yes: bool):
        self._remove_confirmation_buttons()
        self._add_bubble("user", "✅ Ya, lanjutkan" if yes else "❌ Batalkan")
        thinking = self._add_thinking_bubble()
        self._set_input_enabled(False)

        def task():
            try:
                reply = self.agent.resolve_confirmation(yes)
            except Exception as e:
                reply = f"⚠️ Error: {e}"
            self.after(0, lambda: self._finish(thinking, reply))

        threading.Thread(target=task, daemon=True).start()

    def _set_input_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.input_box.configure(state=state)
        self.send_btn.configure(state=state, text="Kirim ➤" if enabled else "...")

    # ── Nav actions ────────────────────────────────────────────

    def _on_new_chat(self):
        self.agent.reset()
        for w in self.chat_frame.winfo_children():
            w.destroy()
        self._confirmation_frame = None
        self._pending_image = None
        if self.img_bar.winfo_ismapped():
            self.img_bar.pack_forget()
        self._add_bubble("assistant", "Percakapan baru dimulai. Ada yang bisa saya bantu?")

    def _on_save_chat(self):
        msgs = self.agent.history
        user_msgs = [m for m in msgs if m.get("role") == "user"]
        title = user_msgs[0]["content"][:30] if user_msgs else "Chat"
        save_chat_history(msgs, title)
        self._add_bubble("system", "✅ Chat disimpan.")

    def _on_show_history(self):
        def on_load(messages):
            self.agent.load_history(messages)
            for w in self.chat_frame.winfo_children():
                w.destroy()
            self._replay_history()
            self._add_bubble("system", "✅ Riwayat chat berhasil dimuat.")
        HistoryPanel(self, on_load_callback=on_load)

    def _on_show_clipboard(self):
        if self._clipboard_panel and self._clipboard_panel.winfo_exists():
            self._clipboard_panel.lift()
            return
        def on_paste(text):
            self.input_box.delete("1.0", "end")
            self.input_box.insert("1.0", text)
        self._clipboard_panel = ClipboardPanel(self, on_paste_callback=on_paste)

    def _on_show_saved_clipboard(self):
        if self._saved_clipboard_panel and self._saved_clipboard_panel.winfo_exists():
            self._saved_clipboard_panel.lift()
            return
        def on_paste(text):
            self.input_box.delete("1.0", "end")
            self.input_box.insert("1.0", text)
        self._saved_clipboard_panel = SavedClipboardPanel(self, on_paste_callback=on_paste)

    # ── Image attach ───────────────────────────────────────────

    def _on_attach_image(self):
        fp = filedialog.askopenfilename(
            title="Pilih Gambar",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.webp *.bmp")]
        )
        if not fp:
            return
        try:
            with open(fp, "rb") as f:
                raw = f.read()
            b64 = base64.b64encode(raw).decode("utf-8")
            ext = Path(fp).suffix.lower()
            mt_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                      ".png": "image/png", ".gif": "image/gif",
                      ".webp": "image/webp", ".bmp": "image/bmp"}
            mt = mt_map.get(ext, "image/jpeg")
            self._pending_image = {"base64": b64, "media_type": mt}

            for w in self.img_bar.winfo_children():
                w.destroy()
            ctk.CTkLabel(self.img_bar,
                         text=f"🖼️  {Path(fp).name}  — siap dikirim",
                         font=ctk.CTkFont(size=12), text_color=C_TEXT).pack(side="left", padx=16, pady=8)
            ctk.CTkButton(self.img_bar, text="✕", width=30, height=30,
                          fg_color="transparent", hover_color=C_BORDER,
                          text_color=C_MUTED, command=self._cancel_image).pack(side="right", padx=8)
            self.img_bar.pack(fill="x", before=self.chat_frame)
        except Exception as e:
            messagebox.showerror("Error", f"Gagal buka gambar: {e}")

    def _cancel_image(self):
        self._pending_image = None
        self.img_bar.pack_forget()

    # ── Voice input (Groq Whisper) ─────────────────────────────

    def _on_voice_input(self):
        if self._is_recording:
            return
        self._is_recording = True
        self.voice_btn.configure(text="🔴 Rekam...", fg_color=C_RED, state="disabled")

        def task():
            audio_path = None
            try:
                # Install pyaudio kalau belum ada
                try:
                    import pyaudio
                except ImportError:
                    import subprocess
                    subprocess.run(["pip3", "install", "pyaudio", "--break-system-packages"],
                                   capture_output=True)
                    import pyaudio

                # Update UI: sedang merekam
                self.after(0, lambda: self.voice_btn.configure(text="🎙 Mendengar..."))

                # Rekam audio dengan VAD
                audio_path = _record_audio_pyaudio(
                    duration_max=30, silence_timeout=1.5,
                    stop_flag=lambda: self._is_closing
                )

                # Update UI: sedang transkripsi
                self.after(0, lambda: self.voice_btn.configure(text="⏳ Proses..."))

                # Transkripsi: Groq Whisper jika API key ada dan internet, else Google
                if GROQ_API_KEY and _check_internet_quick():
                    text = _transcribe_groq_whisper(audio_path)
                else:
                    text = _transcribe_google_fallback(audio_path)

                if text:
                    self.after(0, lambda: self._insert_voice_text(text))
                else:
                    self.after(0, lambda: self._add_bubble("system", "⚠️ Tidak ada suara yang terdeteksi."))

            except Exception as e:
                err = str(e)
                self.after(0, lambda: self._add_bubble("system", f"⚠️ Voice error: {err}"))
            finally:
                if audio_path and os.path.exists(audio_path):
                    try:
                        os.unlink(audio_path)
                    except Exception:
                        pass
                self._is_recording = False
                self.after(0, lambda: self.voice_btn.configure(
                    text="🎤 Suara", fg_color="transparent", state="normal"
                ))

        threading.Thread(target=task, daemon=True).start()

    def _insert_voice_text(self, text: str):
        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", text)
        self.input_box.focus_set()

    # ── Helpers ────────────────────────────────────────────────

    @staticmethod
    def _fmt(args: dict) -> str:
        parts = []
        for k, v in args.items():
            s = str(v)
            parts.append(f"{k}={s[:30]}{'...' if len(s) > 30 else ''}")
        return ", ".join(parts)


def _check_internet_quick() -> bool:
    import socket
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except Exception:
        return False


def run_gui():
    app = ChatWindow()
    app.mainloop()
