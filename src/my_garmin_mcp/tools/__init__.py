from mcp.server.mcpserver import MCPServer

from . import ping


def register_tools(server: MCPServer) -> None:
    """Add new tool modules here: one file per tool, each exposing register(server)."""
    ping.register(server)
