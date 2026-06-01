from __future__ import annotations

from urllib.parse import urlsplit


def https_url_only(text: str) -> str | None:
    """Return a URL only when the whole user message is one HTTPS URL."""
    candidate = text.strip()
    if not candidate or any(character.isspace() for character in candidate):
        return None
    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError:
        return None
    if parsed.scheme.lower() != "https" or not parsed.netloc or not parsed.hostname:
        return None
    if parsed.username is not None or parsed.password is not None or port is None and ":" in parsed.hostname:
        return None
    return candidate


def is_https_url_only(text: str) -> bool:
    return https_url_only(text) is not None
