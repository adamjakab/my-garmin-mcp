from mcp.server.mcpserver import MCPServer

from ..garmin import GarminClient
from . import ping


def register_tools(server: MCPServer, garmin: GarminClient) -> None:
    """Add new tool modules here: one file per tool, each exposing register(server, garmin)."""
    ping.register(server)
