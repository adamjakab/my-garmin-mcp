from datetime import UTC, datetime

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from .. import __version__


def register(server: MCPServer) -> None:
    @server.tool(
        name="ping",
        title="Ping",
        description="Health check. Replies with pong, the server version and the server time.",
        annotations=ToolAnnotations(read_only_hint=True),
    )
    def ping() -> str:
        return f"pong v{__version__} {datetime.now(UTC).isoformat(timespec='milliseconds').replace('+00:00', 'Z')}"
