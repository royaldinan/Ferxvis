"""
Tool untuk membaca dan mengirim email lewat Gmail API resmi (OAuth).

TIDAK PERNAH menyimpan password asli kamu. Menggunakan OAuth flow resmi Google:
1. Kamu setup credentials.json dari Google Cloud Console (lihat README.md)
2. Saat pertama kali dipakai, browser akan terbuka minta kamu login & izinkan akses
3. Token hasil login disimpan di gmail_token.json (lokal, di laptop kamu sendiri)

send_email ada di TOOLS_REQUIRING_CONFIRMATION (config.py), jadi akan selalu minta
konfirmasi user dulu sebelum benar-benar terkirim - lihat core/agent.py.
"""

import base64
import os
from email.mime.text import MIMEText

from config import GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GMAIL_LIBS_AVAILABLE = True
except ImportError:
    GMAIL_LIBS_AVAILABLE = False


class GmailNotConfiguredError(Exception):
    pass


def _get_credentials():
    """
    Ambil credentials OAuth yang valid. Kalau token belum ada atau expired,
    akan memicu login flow lewat browser (hanya terjadi sekali, lalu token disimpan).
    """
    if not GMAIL_LIBS_AVAILABLE:
        raise GmailNotConfiguredError(
            "Library Gmail belum terinstall. Jalankan: "
            "pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client"
        )

    if not os.path.exists(GMAIL_CREDENTIALS_FILE):
        raise GmailNotConfiguredError(
            f"File credentials.json tidak ditemukan di {GMAIL_CREDENTIALS_FILE}. "
            "Lihat README.md bagian 'Setup Email (Gmail)' untuk cara mendapatkannya dari "
            "Google Cloud Console."
        )

    creds = None
    if os.path.exists(GMAIL_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(GMAIL_TOKEN_FILE, "w") as token_file:
            token_file.write(creds.to_json())

    return creds


def read_inbox(max_results: int = 5) -> str:
    """Baca beberapa email terbaru dari inbox (subjek, pengirim, ringkasan singkat)."""
    try:
        creds = _get_credentials()
    except GmailNotConfiguredError as e:
        return f"ERROR: {e}"

    try:
        service = build("gmail", "v1", credentials=creds)
        results = service.users().messages().list(
            userId="me", maxResults=max(1, min(max_results, 20)), labelIds=["INBOX"]
        ).execute()
        messages = results.get("messages", [])

        if not messages:
            return "Inbox kosong, tidak ada email."

        lines = []
        for i, msg_ref in enumerate(messages, 1):
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            snippet = msg.get("snippet", "")
            lines.append(
                f"{i}. Dari: {headers.get('From', '(tidak diketahui)')}\n"
                f"   Subjek: {headers.get('Subject', '(tanpa subjek)')}\n"
                f"   Tanggal: {headers.get('Date', '')}\n"
                f"   Ringkasan: {snippet}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"ERROR saat membaca inbox: {e}"


def search_email(query: str, max_results: int = 5) -> str:
    """
    Cari email berdasarkan query Gmail search syntax, contoh:
    'from:budi@example.com', 'subject:invoice', 'is:unread'.
    """
    try:
        creds = _get_credentials()
    except GmailNotConfiguredError as e:
        return f"ERROR: {e}"

    try:
        service = build("gmail", "v1", credentials=creds)
        results = service.users().messages().list(
            userId="me", q=query, maxResults=max(1, min(max_results, 20))
        ).execute()
        messages = results.get("messages", [])

        if not messages:
            return f"Tidak ada email yang cocok dengan pencarian: '{query}'."

        lines = []
        for i, msg_ref in enumerate(messages, 1):
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            lines.append(
                f"{i}. Dari: {headers.get('From', '?')} | Subjek: {headers.get('Subject', '?')} "
                f"| {headers.get('Date', '')}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"ERROR saat mencari email: {e}"


def send_email(to: str, subject: str, body: str) -> str:
    """
    Kirim email lewat akun Gmail yang sudah terhubung.
    PENTING: tool ini wajib konfirmasi user dulu (diatur di config.py TOOLS_REQUIRING_CONFIRMATION).
    """
    if not to or "@" not in to:
        return f"ERROR: alamat email tujuan '{to}' tidak valid."

    try:
        creds = _get_credentials()
    except GmailNotConfiguredError as e:
        return f"ERROR: {e}"

    try:
        service = build("gmail", "v1", credentials=creds)

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        service.users().messages().send(userId="me", body={"raw": raw}).execute()

        return f"Email berhasil dikirim ke {to} dengan subjek '{subject}'."
    except Exception as e:
        return f"ERROR saat mengirim email: {e}"
