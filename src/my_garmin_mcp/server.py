from mcp.server.mcpserver import MCPServer

from .garmin import GarminClient
from .tools import register_tools


def create_mcp_server(garmin: GarminClient) -> MCPServer:
    server = MCPServer(
        name="my-garmin-mcp",
        version="0.3.0",
        instructions="Personal server for the owner's Garmin data.",
    )
    register_tools(server, garmin)
    return server
