from collections.abc import Callable

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from .auth.middleware import BearerAuthMiddleware
from .server import create_mcp_server


def create_app(verify_key: Callable[[str], bool]) -> Starlette:
    """Streamable HTTP at /mcp, stateless (no sessions to lose on restart), behind a bearer key. /health is open."""
    server = create_mcp_server()

    @server.custom_route("/health", methods=["GET"])
    async def health(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    app = server.streamable_http_app(stateless_http=True, json_response=True)
    app.add_middleware(BearerAuthMiddleware, verify=verify_key)
    return app
