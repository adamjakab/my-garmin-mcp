from mcp.server.mcpserver import MCPServer

from ..garmin import GarminClient
from . import (
    activities,
    activity,
    body_battery,
    daily_summary,
    heart_rate,
    hrv,
    ping,
    respiration,
    resting_hr,
    sleep,
    spo2,
    stress,
    training_readiness,
    vo2max,
    weight,
)


def register_tools(server: MCPServer, garmin: GarminClient) -> None:
    """Add new tool modules here: one file per tool, each exposing register(server, garmin)."""
    ping.register(server)
    for module in (
        sleep,
        hrv,
        body_battery,
        heart_rate,
        resting_hr,
        stress,
        spo2,
        respiration,
        training_readiness,
        vo2max,
        weight,
        daily_summary,
        activities,
        activity,
    ):
        module.register(server, garmin)
