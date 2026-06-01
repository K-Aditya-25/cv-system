from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Iterable
from urllib.parse import SplitResult, urlsplit, urlunsplit


class UnsafeUrlError(ValueError):
    pass


Resolver = Callable[..., Iterable[tuple]]


def _addresses(host: str, port: int, resolver: Resolver) -> set[str]:
    try:
        return {item[4][0] for item in resolver(host, port, type=socket.SOCK_STREAM)}
    except OSError as error:
        raise UnsafeUrlError("host could not be resolved") from error


def validate_public_https_url(url: str, resolver: Resolver = socket.getaddrinfo) -> str:
    try:
        parsed = urlsplit(url)
        port = parsed.port or 443
    except ValueError as error:
        raise UnsafeUrlError("invalid URL") from error
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise UnsafeUrlError("only HTTPS URLs are allowed")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeUrlError("URL credentials are not allowed")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost") or not host:
        raise UnsafeUrlError("local hosts are not allowed")
    addresses = _addresses(host, port, resolver)
    if not addresses or any(not ipaddress.ip_address(value).is_global for value in addresses):
        raise UnsafeUrlError("host does not resolve exclusively to public IP addresses")
    netloc = f"[{host}]" if ":" in host else host
    if parsed.port is not None:
        netloc += f":{parsed.port}"
    normalized = SplitResult("https", netloc, parsed.path or "/", parsed.query, "")
    return urlunsplit(normalized)
