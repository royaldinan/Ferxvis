"""
LLM Client - Groq API (online, gratis, cepat) atau Ollama (offline).
Model: llama-3.3-70b-versatile untuk chat/tools, llama-3.2-90b-vision untuk gambar.
Groq free tier: ~14,400 req/hari, 30 req/menit — sangat cukup untuk pemakaian harian.
"""

import json
import urllib.request
import urllib.error
import socket
import base64

from config import (OLLAMA_HOST, MODEL_NAME, GROQ_API_KEY,
                    GROQ_MODEL, GROQ_VISION_MODEL)


class LLMError(Exception):
    pass

# Alias untuk backward compat
OllamaError = LLMError


# ── Quota tracking (dari response headers Groq) ────────────────
# Diupdate setiap kali _chat_groq() sukses dapat response.
# GUI bisa baca ini lewat get_quota_info() untuk nampilin sisa kuota.
_quota_state = {
    "limit_requests": None,      # RPD total (mis. 1000)
    "remaining_requests": None,  # RPD sisa
    "reset_requests": None,      # string mis. "2m59.56s"
    "limit_tokens": None,        # TPM total
    "remaining_tokens": None,    # TPM sisa
    "reset_tokens": None,
    "last_updated": None,        # datetime ISO string
    "model": None,
}


def _update_quota_from_headers(headers, model: str):
    """Simpan info rate-limit dari response headers Groq ke state global."""
    import datetime as _dt
    try:
        def _to_int(v):
            return int(v) if v is not None and str(v).strip() != "" else None

        _quota_state["limit_requests"] = _to_int(headers.get("x-ratelimit-limit-requests"))
        _quota_state["remaining_requests"] = _to_int(headers.get("x-ratelimit-remaining-requests"))
        _quota_state["reset_requests"] = headers.get("x-ratelimit-reset-requests")
        _quota_state["limit_tokens"] = _to_int(headers.get("x-ratelimit-limit-tokens"))
        _quota_state["remaining_tokens"] = _to_int(headers.get("x-ratelimit-remaining-tokens"))
        _quota_state["reset_tokens"] = headers.get("x-ratelimit-reset-tokens")
        _quota_state["last_updated"] = _dt.datetime.now().isoformat()
        _quota_state["model"] = model
    except Exception:
        pass  # quota tracking tidak boleh sampai bikin chat gagal


def get_quota_info() -> dict:
    """Ambil snapshot info kuota terakhir. Return dict kosong-aman kalau belum ada data."""
    return dict(_quota_state)


# ── Connectivity checks ────────────────────────────────────────

def _check_internet() -> bool:
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except Exception:
        return False


def check_ollama_running() -> bool:
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def check_model_available(model_name: str = MODEL_NAME) -> bool:
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m["name"] for m in data.get("models", [])]
            return any(m == model_name or m.startswith(model_name.split(":")[0]) for m in models)
    except Exception:
        return False


def get_active_mode() -> str:
    if GROQ_API_KEY and _check_internet():
        return "groq"
    return "ollama"


# ── Main chat entry ────────────────────────────────────────────

def chat(messages: list, tools: list = None, image_data: dict = None,
         temperature: float = 0.4) -> dict:
    mode = get_active_mode()
    if mode == "groq":
        return _chat_groq(messages, tools, image_data, temperature)
    else:
        return _chat_ollama(messages, tools, temperature)


# ── Groq API (OpenAI-compatible) ──────────────────────────────

def _chat_groq(messages: list, tools: list = None, image_data: dict = None,
               temperature: float = 0.4) -> dict:
    """
    Chat via Groq API.
    - Dengan gambar: pakai GROQ_VISION_MODEL (llama-3.2-90b-vision-preview)
    - Tanpa gambar:  pakai GROQ_MODEL (llama-3.3-70b-versatile) + tool calling
    """
    has_image = bool(image_data)
    model = GROQ_VISION_MODEL if has_image else GROQ_MODEL

    # ── Build pesan format OpenAI ──────────────────────────────
    groq_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            groq_messages.append({"role": "system", "content": content})

        elif role == "user":
            groq_messages.append({"role": "user", "content": content})

        elif role == "assistant":
            m = {"role": "assistant", "content": content or ""}
            if msg.get("tool_calls"):
                # Groq mewajibkan tool_calls[].function.arguments berupa STRING JSON,
                # bukan dict. Internal state kita simpan sebagai dict (parsed),
                # jadi harus di-serialize ulang di sini sebelum dikirim ke API.
                fixed_tool_calls = []
                for tc in msg["tool_calls"]:
                    tc_copy = json.loads(json.dumps(tc))  # deep copy aman
                    fn = tc_copy.get("function", {})
                    args = fn.get("arguments", "{}")
                    if not isinstance(args, str):
                        args = json.dumps(args)
                    fn["arguments"] = args
                    fixed_tool_calls.append(tc_copy)
                m["tool_calls"] = fixed_tool_calls
            groq_messages.append(m)

        elif role == "tool":
            # Tool results → user message supaya kompatibel
            groq_messages.append({
                "role": "user",
                "content": f"[Hasil tool]: {content}"
            })

    # ── Inject gambar ke pesan user terakhir ──────────────────
    if has_image:
        for i in range(len(groq_messages) - 1, -1, -1):
            if groq_messages[i]["role"] == "user":
                text = groq_messages[i].get("content", "")
                groq_messages[i]["content"] = [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": (
                                f"data:{image_data['media_type']};base64,"
                                f"{image_data['base64']}"
                            )
                        }
                    },
                    {"type": "text", "text": text or "Analisis gambar ini."}
                ]
                break

    # ── Build payload ──────────────────────────────────────────
    payload = {
        "model": model,
        "messages": groq_messages,
        "temperature": temperature,
        "max_tokens": 2048,
    }

    # Tool calling hanya untuk non-vision request
    if tools and not has_image:
        groq_tools = []
        for t in tools:
            fn = t.get("function", {})
            params = fn.get("parameters", {"type": "object", "properties": {}})
            # Bersihkan parameter yang mungkin bikin error
            params = _sanitize_params(params)
            groq_tools.append({
                "type": "function",
                "function": {
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "parameters": params,
                }
            })
        payload["tools"] = groq_tools
        payload["tool_choice"] = "auto"

    # ── HTTP request (pakai requests library, lebih reliable dari urllib) ──
    try:
        import requests as _requests
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        }
        resp = _requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=30,
        )
        if not resp.ok:
            _update_quota_from_headers(resp.headers, model)  # headers tetap ada walau 429
            try:
                err_msg = resp.json().get("error", {}).get("message", resp.text)
            except Exception:
                err_msg = resp.text
            if resp.status_code == 429:
                retry_after = resp.headers.get("retry-after", "")
                reset_req = resp.headers.get("x-ratelimit-reset-requests", "")
                raise LLMError(
                    f"Groq API limit harian tercapai (429). "
                    f"Reset dalam: {reset_req or retry_after or 'tidak diketahui'}."
                )
            raise LLMError(f"Groq API error {resp.status_code}: {err_msg}")
        result = resp.json()
        _update_quota_from_headers(resp.headers, model)
    except LLMError:
        raise
    except Exception as e:
        raise LLMError(f"Groq error: {e}")

    # ── Parse response ─────────────────────────────────────────
    if "choices" not in result or not result["choices"]:
        raise LLMError(f"Response tidak valid dari Groq: {result}")

    choice = result["choices"][0]
    message = choice.get("message", {})

    content = message.get("content") or ""
    tool_calls_raw = message.get("tool_calls") or []

    # Convert tool_calls ke format internal
    tool_calls = []
    for tc in tool_calls_raw:
        fn = tc.get("function", {})
        args = fn.get("arguments", "{}")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}
        tool_calls.append({
            "id": tc.get("id", ""),
            "type": tc.get("type", "function"),  # WAJIB ada, Groq menolak history tanpa ini
            "function": {
                "name": fn.get("name", ""),
                "arguments": args,
            }
        })

    out = {"message": {"content": content, "role": "assistant"}}
    if tool_calls:
        out["message"]["tool_calls"] = tool_calls

    return out


def _sanitize_params(params: dict) -> dict:
    """Bersihkan schema parameter supaya aman di Groq."""
    if not isinstance(params, dict):
        return params

    REMOVE_KEYS = {"$schema", "additionalProperties", "default", "examples", "title"}
    result = {}

    for k, v in params.items():
        if k in REMOVE_KEYS:
            continue
        if isinstance(v, dict):
            result[k] = _sanitize_params(v)
        elif isinstance(v, list):
            result[k] = [_sanitize_params(i) if isinstance(i, dict) else i for i in v]
        else:
            result[k] = v

    return result


# ── Ollama fallback (offline) ──────────────────────────────────

def _chat_ollama(messages: list, tools: list = None, temperature: float = 0.4) -> dict:
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if tools:
        payload["tools"] = tools

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise LLMError(
            f"Tidak bisa terhubung ke Ollama. Jalankan 'ollama serve'. Detail: {e}"
        )
    except Exception as e:
        raise LLMError(f"Error Ollama: {e}")
