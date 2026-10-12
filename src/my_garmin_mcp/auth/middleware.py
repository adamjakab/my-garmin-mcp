import json
import re
from collections.abc import Callable

from starlette.types import ASGIApp, Receive, Scope, Send

_BEARER = re.compile(r"^Bearer (.+)$", re.IGNORECASE)
_UNAUTHORIZED = json.dumps(
    {"jsonrpc": "2.0", "error": {"code": -32001, "message": "Unauthorized"}, "id": None}
).encode()


class BearerAuthMiddleware:
    """Pure-ASGI bearer check. Everything except the paths in `public` requires a valid key."""

    def __init__(self, app: ASGIApp, verify: Callable[[str], bool], public: frozenset[str] = frozenset({"/health"})):
        self.app = app
        self.verify = verify
        self.public = public

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in self.public:
            await self.app(scope, receive, send)
            return
        headers = {k.lower(): v for k, v in scope["headers"]}
        match = _BEARER.match(headers.get(b"authorization", b"").decode("latin-1"))
        if not match or not self.verify(match.group(1)):
            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"www-authenticate", b"Bearer"),
                        (b"content-length", str(len(_UNAUTHORIZED)).encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": _UNAUTHORIZED})
            return
        await self.app(scope, receive, send)
