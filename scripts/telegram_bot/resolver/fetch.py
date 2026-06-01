from __future__ import annotations

from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import HTTPRedirectHandler, Request, build_opener

from scripts.telegram_bot.resolver_models import FetchedPage

from .security import validate_public_https_url


class FetchError(ValueError):
    pass


@dataclass(frozen=True)
class FetchResult:
    url: str
    html: str


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _body(response, max_bytes: int) -> tuple[str, bytes]:
    content_type = response.headers.get_content_type()
    if content_type not in {"text/html", "application/xhtml+xml"}:
        raise FetchError(f"unsupported content type: {content_type}")
    length = response.headers.get("Content-Length")
    if length and int(length) > max_bytes:
        raise FetchError("response exceeds byte limit")
    body = response.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise FetchError("response exceeds byte limit")
    return response.headers.get("Content-Type", content_type), body


def fetch_html(url: str, *, timeout: float = 8, max_bytes: int = 1_000_000,
               max_redirects: int = 4, validate=validate_public_https_url,
               opener=None) -> FetchedPage:
    current = validate(url)
    requested = current
    client = opener or build_opener(_NoRedirect)
    for attempt in range(max_redirects + 1):
        request = Request(current, headers={"User-Agent": "cv-system-job-resolver/1"})
        try:
            with client.open(request, timeout=timeout) as response:
                final_url = validate(response.geturl())
                content_type, body = _body(response, max_bytes)
                return FetchedPage(requested, final_url, content_type, body)
        except HTTPError as error:
            if error.code not in {301, 302, 303, 307, 308}:
                raise FetchError(f"HTTP {error.code}") from error
            location = error.headers.get("Location")
            if not location or attempt == max_redirects:
                raise FetchError("redirect limit exceeded") from error
            current = validate(urljoin(current, location))
        except (OSError, ValueError) as error:
            raise FetchError(str(error)) from error
    raise FetchError("redirect limit exceeded")
