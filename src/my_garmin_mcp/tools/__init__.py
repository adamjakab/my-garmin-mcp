from mcp.server.mcpserver import MCPServer

from ..garmin import GarminClient
from . import activities, activity, heart_rate, hrv, ping, resting_hr, sleep, vo2max, weight


def register_tools(server: MCPServer, garmin: GarminClient) -> None:
    """Add new tool modules here: one file per tool, each exposing register(server, garmin)."""
    ping.register(server)
    for module in (sleep, hrv, heart_rate, resting_hr, vo2max, weight, activities, activity):
        module.register(server, garmin)
