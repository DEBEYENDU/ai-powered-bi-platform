"""Cheap TCP reachability probe for service endpoints.

Problem this solves: when Redis/Celery's broker is not running, every
redis-py / kombu probe burns ~4s in retries, so ``/admin/overview``
(which runs health checks + queue stats) took ~12s and the dashboard
felt frozen. Probing the socket first keeps the reported status honest
(still ``down`` / ``unreachable``) but answers in a few hundred ms.

A short negative cache keeps three probes against the same dead endpoint
(redis check, workers check, queue stats) from paying the wait three times
in a single request.
"""

from __future__ import annotations

import socket
import time
from urllib.parse import urlparse

DEFAULT_PORTS = {
    "redis": 6379,
    "rediss": 6379,
    "amqp": 5672,
    "amqps": 5671,
    "http": 80,
    "https": 443,
}

# Total per-probe budget; split across resolved addresses (::1 + 127.0.0.1).
DEFAULT_TIMEOUT = 0.3
# How long a failed probe is remembered before retrying.
NEGATIVE_TTL = 5.0

_negative: dict[tuple[str, int], tuple[float, str]] = {}


def endpoint_of(url: str) -> tuple[str, int] | None:
    """Return (host, port) for a URL, or None when no TCP endpoint applies."""
    try:
        parsed = urlparse(url or "")
        host = parsed.hostname
        if not host:
            return None
        port = parsed.port or DEFAULT_PORTS.get(parsed.scheme)
        if not port:
            return None
        return str(host), int(port)
    except Exception:
        return None


def tcp_reachable(url: str, timeout: float = DEFAULT_TIMEOUT) -> tuple[bool, str]:
    """True when a TCP connection to the URL's endpoint succeeds.

    Returns ``(False, reason)`` for refused/timed-out/unresolvable endpoints.
    URLs with no TCP endpoint (``memory://``, ``filesystem://``, ...) return
    ``(False, "no tcp endpoint")`` — callers should skip the fast path when
    :func:`endpoint_of` returns None.
    """
    endpoint = endpoint_of(url)
    if endpoint is None:
        return False, "no tcp endpoint"
    host, port = endpoint

    now = time.monotonic()
    cached = _negative.get(endpoint)
    if cached is not None and now - cached[0] < NEGATIVE_TTL:
        return False, cached[1]

    ok, reason = _probe(host, port, timeout)
    if ok:
        _negative.pop(endpoint, None)
        return True, f"{host}:{port}"
    _negative[endpoint] = (time.monotonic(), reason)
    return False, reason


def _probe(host: str, port: int, timeout: float) -> tuple[bool, str]:
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        return False, f"{host}:{port} unreachable ({exc.strerror or exc})"
    if not addresses:
        return False, f"{host}:{port} unreachable (no addresses)"
    # Windows drops SYNs to closed local ports instead of rejecting them, so
    # each family can burn the whole timeout — split the budget across them.
    slice_timeout = max(timeout / len(addresses), 0.05)
    last_error: OSError | None = None
    for family, socktype, proto, _canon, sockaddr in addresses:
        try:
            with socket.socket(family, socktype, proto) as sock:
                sock.settimeout(slice_timeout)
                sock.connect(sockaddr)
            return True, f"{host}:{port}"
        except OSError as exc:
            last_error = exc
    detail = (last_error.strerror or str(last_error)) if last_error else "no route"
    return False, f"{host}:{port} unreachable ({detail})"
