"""The client IP comes from X-Forwarded-For only behind a trusted proxy (uvicorn)."""

import asyncio

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


async def _client_async(trusted: str, peer: str, forwarded: str | None) -> str:
    seen: dict[str, str] = {}

    async def app(scope: dict, receive: object, send: object) -> None:  # type: ignore[type-arg]
        seen["client"] = scope["client"][0]

    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    scope = {"type": "http", "client": (peer, 1234), "headers": headers, "scheme": "http"}
    await ProxyHeadersMiddleware(app, trusted_hosts=trusted)(scope, None, None)  # type: ignore[arg-type]
    return seen["client"]


def _client_of(trusted: str, peer: str, forwarded: str | None) -> str:
    return asyncio.run(_client_async(trusted, peer, forwarded))


def test_ingress_is_trusted() -> None:
    assert _client_of("100.121.0.0/16", "100.121.49.66", "203.0.113.7") == "203.0.113.7"


def test_chain_takes_the_first_untrusted_address_from_the_right() -> None:
    forwarded = "198.51.100.1, 203.0.113.7, 100.121.49.66"  # forged left part, real client, ingress
    assert _client_of("100.121.0.0/16", "100.121.38.160", forwarded) == "203.0.113.7"


def test_untrusted_peer_cannot_set_its_ip() -> None:
    assert _client_of("100.121.0.0/16", "198.51.100.9", "203.0.113.7") == "198.51.100.9"
