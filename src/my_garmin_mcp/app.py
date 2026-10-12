from collections.abc import Callable, Sequence

from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from .auth.middleware import BearerAuthMiddleware
from .garmin import GarminClient
from .server import create_mcp_server


def create_app(verify_key: Callable[[str], bool], garmin: GarminClient, allowed_hosts: Sequence[str] = ()) -> Starlette:
    """Streamable HTTP at /mcp, stateless (no sessions to lose on restart), behind a bearer key. /health is open."""
    server = create_mcp_server(garmin)

    @server.custom_route("/health", methods=["GET"])
    async def health(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    # The SDK rejects Host headers it does not know (DNS rebinding protection). Loopback is always fine; the public
    # hostname used behind NGINX goes into ALLOWED_HOSTS.
    security = TransportSecuritySettings(
        allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*", *allowed_hosts],
    )
    app = server.streamable_http_app(stateless_http=True, json_response=True, transport_security=security)
    app.add_middleware(BearerAuthMiddleware, verify=verify_key)
    return app
