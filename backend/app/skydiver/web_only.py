"""Closed beta (#161): the API answers only requests that came through the web server.

The web server sends SKYDIVER_WEB_PROXY_KEY with every call. With
SKYDIVER_REQUIRE_PROXY_KEY on, any other request gets the same plain 404 as an
unknown address, so the API reveals nothing to direct callers; the health check
stays open for the host's checks and the status page. Off locally and in tests.
"""

import hmac

from starlette.types import ASGIApp, Receive, Scope, Send

PROXY_KEY_HEADER = b"x-organiser-proxy-key"
OPEN_PATHS = frozenset({"/api/skydiver/v1/health"})
_NOT_FOUND = b'{"detail":"Not Found"}'


class WebOnly:
    def __init__(self, app: ASGIApp, *, proxy_key: str) -> None:
        self.app = app
        self.key = proxy_key.encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in OPEN_PATHS:
            await self.app(scope, receive, send)
            return
        supplied = b""
        for name, value in scope["headers"]:
            if name == PROXY_KEY_HEADER:
                supplied = value
                break
        if supplied and hmac.compare_digest(supplied, self.key):
            await self.app(scope, receive, send)
            return
        await send(
            {
                "type": "http.response.start",
                "status": 404,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(_NOT_FOUND)).encode()),
                    (b"cache-control", b"no-store"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": _NOT_FOUND})
