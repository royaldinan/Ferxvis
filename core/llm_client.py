"""
LLM Client — full Ollama lokal dengan CUDA.
"""

import json
import urllib.request
import urllib.error

from config import OLLAMA_HOST, OLLAMA_MODEL_NAME


class OllamaError(Exception):
    pass


def check_ollama_running() -> bool:
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def check_model_available(model_name: str = None) -> bool:
    model_name = model_name or OLLAMA_MODEL_NAME
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m["name"] for m in data.get("models", [])]
            return any(m == model_name or m.startswith(model_name.split(":")[0]) for m in models)
    except Exception:
        return False


def _clean_messages(messages: list) -> list:
    cleaned = []
    for m in messages:
        role = m.get("role")
        if role == "tool":
            cleaned.append({"role": "tool", "content": m.get("content", "")})
        elif role == "assistant":
            msg = {"role": "assistant", "content": m.get("content", "") or ""}
            if m.get("tool_calls"):
                clean_calls = []
                for call in m["tool_calls"]:
                    func = call.get("function", {})
                    args = func.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {}
                    clean_calls.append({
                        "function": {
                            "name": func.get("name", ""),
                            "arguments": args,
                        }
                    })
                msg["tool_calls"] = clean_calls
            cleaned.append(msg)
        else:
            cleaned.append({"role": role, "content": m.get("content", "")})
    return cleaned


def chat(messages: list, tools: list = None, temperature: float = 0.4) -> dict:
    messages = _clean_messages(messages)
    payload = {
        "model": OLLAMA_MODEL_NAME,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_gpu": 99,      # pakai semua layer GPU (CUDA)
        },
        "tools": tools if tools else [],
    }

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
        raise OllamaError(
            f"Tidak bisa terhubung ke Ollama di {OLLAMA_HOST}. "
            f"Pastikan Ollama sudah jalan (jalankan 'ollama serve'). Detail: {e}"
        )
    except Exception as e:
        raise OllamaError(f"Error saat memanggil Ollama: {e}")
