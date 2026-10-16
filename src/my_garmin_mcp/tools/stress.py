from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from ..garmin import GarminClient
from ..garmin.dates import MAX_DAYS_STRESS
from ..garmin.extract import stress_day
from ._common import EndDate, StartDate, as_json, per_day


def register(server: MCPServer, garmin: GarminClient) -> None:
    @server.tool(
        name="get_stress",
        title="All-day stress",
        description=(
            "All-day stress per day: average and max stress level (0-100), minutes in rest/low/medium/high stress, "
            "plus [local time, level] readings per 30-minute bucket. "
            f"At most {MAX_DAYS_STRESS} days per call; days without data are left out."
        ),
        annotations=ToolAnnotations(read_only_hint=True),
    )
    async def get_stress(start_date: StartDate, end_date: EndDate) -> str:
        days = await per_day(
            garmin,
            start_date,
            end_date,
            MAX_DAYS_STRESS,
            lambda g, d: g.get_stress_data(d),
            stress_day,
        )
        return as_json({"start_date": start_date, "end_date": end_date, "count": len(days), "stress": days})
