from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from ..garmin import GarminClient
from ..garmin.dates import MAX_DAYS_PER_DAY_TOOLS
from ..garmin.extract import resting_hr
from ._common import EndDate, StartDate, as_json, per_day


def register(server: MCPServer, garmin: GarminClient) -> None:
    @server.tool(
        name="get_resting_hr",
        title="Resting heart rate",
        description=(
            "Resting heart rate (beats per minute) per day for a date range. "
            f"At most {MAX_DAYS_PER_DAY_TOOLS} days per call; days without a value are left out."
        ),
        annotations=ToolAnnotations(read_only_hint=True),
    )
    async def get_resting_hr(start_date: StartDate, end_date: EndDate) -> str:
        days = await per_day(
            garmin, start_date, end_date, MAX_DAYS_PER_DAY_TOOLS, lambda g, d: g.get_rhr_day(d), resting_hr
        )
        return as_json({"start_date": start_date, "end_date": end_date, "count": len(days), "resting_hr": days})
