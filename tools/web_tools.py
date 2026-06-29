"""
Web search tools - pakai DuckDuckGo (gratis, tanpa API key)
"""

import urllib.request
import urllib.parse
import json
import re


def search_web(query: str, max_results: int = 5) -> str:
    """Cari info terkini via DuckDuckGo Instant Answer API."""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Ferxvis/2.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results = []

        # Abstract (ringkasan utama)
        if data.get("AbstractText"):
            results.append(f"📋 {data['AbstractText']}")
            if data.get("AbstractURL"):
                results.append(f"   Sumber: {data['AbstractURL']}")

        # Answer langsung
        if data.get("Answer"):
            results.append(f"✅ {data['Answer']}")

        # Related topics
        for topic in data.get("RelatedTopics", [])[:max_results - len(results)]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(f"• {topic['Text'][:200]}")

        if not results:
            # Fallback: coba scrape DuckDuckGo HTML (lite)
            return _ddg_html_search(query, max_results)

        return "\n".join(results[:max_results + 2])

    except Exception as e:
        return f"Gagal mencari: {e}"


def _ddg_html_search(query: str, max_results: int = 5) -> str:
    """Fallback search via DuckDuckGo HTML lite."""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Extract snippets sederhana
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
        titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)

        results = []
        for i, (t, s) in enumerate(zip(titles, snippets)):
            if i >= max_results:
                break
            title = re.sub(r'<[^>]+>', '', t).strip()
            snippet = re.sub(r'<[^>]+>', '', s).strip()
            results.append(f"• {title}: {snippet}")

        return "\n".join(results) if results else f"Tidak ada hasil untuk '{query}'."
    except Exception as e:
        return f"Search gagal: {e}"
