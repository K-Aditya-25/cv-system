from __future__ import annotations

import re
from urllib.parse import urlsplit

from scripts.telegram_bot.resolver_models import SearchCandidate


def linkedin_job_id(url: str) -> str | None:
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if not host.endswith("linkedin.com"):
        return None
    if "/jobs/view/" not in parsed.path:
        return None
    match = re.search(r"(\d{6,})", parsed.path)
    return match.group(1) if match else None


def is_linkedin_job_url(url: str) -> bool:
    return linkedin_job_id(url) is not None


def discovery_query(url: str, job_id: str) -> str:
    return f'LinkedIn job {job_id} "{url}"'


def rank_candidates(candidates, source_url: str, job_id: str) -> list[str]:
    urls = {
        _url(candidate).strip()
        for candidate in candidates
        if _url(candidate).strip() and job_id in _url(candidate)
    }
    return sorted(urls, key=lambda url: (-_score(url, source_url, job_id), url))


def _score(url: str, source_url: str, job_id: str) -> int:
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    path = parsed.path.lower()
    score = 0
    score += 100 if job_id in url else 0
    score += 30 if host.endswith("linkedin.com") else 0
    score += 20 if "/jobs/view/" in path else 0
    score += 10 if host != (urlsplit(source_url).hostname or "") else 0
    score -= 50 if any(term in path for term in ("login", "signin", "search")) else 0
    return score


def _url(candidate) -> str:
    return candidate if isinstance(candidate, str) else candidate.url
