from datetime import UTC, datetime

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations


def register(server: MCPServer) -> None:
    @server.tool(
        name="ping",
        title="Ping",
        description="Health check. Replies with pong and the server time.",
        annotations=ToolAnnotations(read_only_hint=True),
    )
    def ping() -> str:
        return f"pong {datetime.now(UTC).isoformat(timespec='milliseconds').replace('+00:00', 'Z')}"
