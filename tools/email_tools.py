"""
Gmail/Google Workspace tools - multi-akun via OAuth2.
Setup per akun: taruh credentials_<nama akun>.json (dari Google Cloud Console)
di folder ferxvis, sesuai path di config.EMAIL_ACCOUNTS.
"""

import os
from config import EMAIL_ACCOUNTS, DEFAULT_EMAIL_ACCOUNT

# Cache service per akun supaya tidak re-auth tiap panggilan
_service_cache = {}


def _resolve_account(account: str = None) -> dict:
    """Validasi nama akun, fallback ke default. Return dict info akun."""
    account = account or DEFAULT_EMAIL_ACCOUNT
    if account not in EMAIL_ACCOUNTS:
        valid = ", ".join(EMAIL_ACCOUNTS.keys())
        raise ValueError(f"Akun '{account}' tidak dikenali. Akun valid: {valid}")
    return EMAIL_ACCOUNTS[account]


def _get_service(account: str = None):
    """Buat Gmail API service dengan OAuth2 untuk akun tertentu."""
    account = account or DEFAULT_EMAIL_ACCOUNT
    if account in _service_cache:
        return _service_cache[account]

    info = _resolve_account(account)
    creds_file = info["credentials_file"]
    token_file = info["token_file"]

    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        SCOPES = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
        ]

        creds = None
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(creds_file):
                    raise FileNotFoundError(
                        f"credentials.json untuk akun '{account}' ({info['address']}) "
                        f"tidak ditemukan di {creds_file}. "
                        "Download dari Google Cloud Console → APIs & Services → Credentials, "
                        f"lalu simpan dengan nama persis: {os.path.basename(creds_file)}"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
                # Saat login, PASTIKAN login dengan akun yang sesuai
                # ({info['address']}) — Google akan tanya akun mana yang dipakai.
                creds = flow.run_local_server(port=0)
            with open(token_file, "w") as f:
                f.write(creds.to_json())

        service = build("gmail", "v1", credentials=creds)
        _service_cache[account] = service
        return service

    except ImportError:
        raise ImportError(
            "Library Gmail belum terinstall. Jalankan:\n"
            "pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
        )


def _format_messages(service, messages) -> str:
    output = []
    for msg in messages:
        m = service.users().messages().get(userId="me", id=msg["id"], format="metadata").execute()
        headers = {h["name"]: h["value"] for h in m["payload"]["headers"]}
        snippet = m.get("snippet", "")[:100]
        output.append(
            f"📧 Dari: {headers.get('From', '?')}\n"
            f"   Subjek: {headers.get('Subject', '(no subject)')}\n"
            f"   {snippet}..."
        )
    return "\n\n".join(output)


def read_inbox(max_results: int = 5, account: str = None) -> str:
    try:
        info = _resolve_account(account)
        service = _get_service(account)
        results = service.users().messages().list(
            userId="me", maxResults=max_results, labelIds=["INBOX"]
        ).execute()
        messages = results.get("messages", [])
        if not messages:
            return f"Inbox akun {info['address']} kosong."
        header = f"📬 Inbox {info['address']}:\n\n"
        return header + _format_messages(service, messages)
    except Exception as e:
        return f"ERROR Gmail: {e}"


def search_email(query: str, max_results: int = 5, account: str = None) -> str:
    try:
        info = _resolve_account(account)
        service = _get_service(account)
        results = service.users().messages().list(
            userId="me", maxResults=max_results, q=query
        ).execute()
        messages = results.get("messages", [])
        if not messages:
            return f"Tidak ada email yang cocok dengan '{query}' di akun {info['address']}."
        header = f"🔍 Hasil pencarian di {info['address']}:\n\n"
        return header + _format_messages(service, messages)
    except Exception as e:
        return f"ERROR Gmail: {e}"


def send_email(to: str, subject: str, body: str, account: str = None) -> str:
    try:
        import base64
        from email.mime.text import MIMEText

        info = _resolve_account(account)
        service = _get_service(account)
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return f"Email berhasil dikirim dari {info['address']} ke {to} dengan subjek '{subject}'."
    except Exception as e:
        return f"ERROR kirim email: {e}"
