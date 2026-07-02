"""
Tool untuk mencari informasi terkini di internet.
Menggunakan Brave Search API (ada free tier 2000 query/bulan).

Setup: daftar di https://brave.com/search/api/, dapatkan API key,
lalu set environment variable BRAVE_API_KEY (lihat README.md).
"""

import json
import urllib.request
import urllib.parse
import urllib.error

from config import BRAVE_API_KEY


def search_web(query: str, max_results: int = 5) -> str:
    """
    Cari informasi di internet berdasarkan query.
    Mengembalikan ringkasan hasil pencarian (judul, snippet, URL) dalam format teks.
    """
    if not BRAVE_API_KEY:
        return (
            "ERROR: Fitur pencarian web belum diaktifkan. Untuk mengaktifkan, daftar gratis di "
            "https://brave.com/search/api/, lalu set environment variable BRAVE_API_KEY "
            "(lihat README.md bagian 'Setup Web Search')."
        )

    if not query or not query.strip():
        return "ERROR: query pencarian tidak boleh kosong."

    max_results = max(1, min(max_results, 10))  # batasi 1-10 supaya hemat kuota & respons tetap ringkas

    params = urllib.parse.urlencode({"q": query.strip(), "count": max_results})
    url = f"https://api.search.brave.com/res/v1/web/search?{params}"

    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "X-Subscription-Token": BRAVE_API_KEY,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return "ERROR: API key Brave Search tidak valid. Cek kembali BRAVE_API_KEY di environment variable."
        if e.code == 429:
            return "ERROR: Kuota pencarian bulan ini sudah habis (rate limit Brave Search API)."
        return f"ERROR: Brave Search API mengembalikan error HTTP {e.code}."
    except urllib.error.URLError as e:
        return f"ERROR: Tidak bisa terhubung ke layanan pencarian. Cek koneksi internet kamu. Detail: {e}"
    except Exception as e:
        return f"ERROR saat melakukan pencarian: {e}"

    results = data.get("web", {}).get("results", [])
    if not results:
        return f"Tidak ada hasil ditemukan untuk pencarian: '{query}'."

    lines = [f"Hasil pencarian untuk '{query}':\n"]
    for i, item in enumerate(results[:max_results], 1):
        title = item.get("title", "(tanpa judul)")
        url_ = item.get("url", "")
        description = item.get("description", "").replace("<strong>", "").replace("</strong>", "")
        lines.append(f"{i}. {title}\n   {description}\n   Sumber: {url_}\n")

    return "\n".join(lines)
