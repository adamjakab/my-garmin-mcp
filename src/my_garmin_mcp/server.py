from mcp.server.mcpserver import MCPServer

from .tools import register_tools


def create_mcp_server() -> MCPServer:
    server = MCPServer(
        name="my-garmin-mcp",
        version="0.2.0",
        instructions="Personal server for the owner's Garmin data.",
    )
    register_tools(server)
    return server
