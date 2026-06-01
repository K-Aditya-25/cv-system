from __future__ import annotations

from urllib.parse import urlsplit


def _url(candidate) -> str:
    return candidate if isinstance(candidate, str) else candidate.url


def rank_url(candidate, source_url: str = "") -> tuple[int, str]:
    url = _url(candidate).strip()
    parsed = urlsplit(url)
    source_host = urlsplit(source_url).hostname or ""
    host = parsed.hostname or ""
    path = parsed.path.lower()
    score = 0
    score += 30 if host == source_host else 0
    score += 12 if any(word in host for word in ("jobs", "careers")) else 0
    score += 10 if any(word in path for word in ("job", "jobs", "career", "position", "vacan")) else 0
    score -= 15 if any(word in path for word in ("login", "signin", "search", "privacy")) else 0
    score -= min(path.count("/"), 8)
    return score, url


def rank_candidates(urls, source_url: str = "") -> list[str]:
    unique = {_url(candidate).strip() for candidate in urls if _url(candidate).strip()}
    return sorted(unique, key=lambda url: (-rank_url(url, source_url)[0], url))
