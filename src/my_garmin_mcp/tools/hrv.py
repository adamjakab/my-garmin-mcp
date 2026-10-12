from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from ..garmin import GarminClient
from ..garmin.dates import MAX_DAYS_PER_DAY_TOOLS
from ..garmin.extract import hrv_summary
from ._common import EndDate, StartDate, as_json, per_day


def register(server: MCPServer, garmin: GarminClient) -> None:
    @server.tool(
        name="get_hrv",
        title="Heart rate variability",
        description=(
            "Overnight heart rate variability (HRV, in ms) per day for a date range: last night's average and "
            "5-minute high, the weekly average, the status (e.g. BALANCED) and the personal baseline range. "
            "The raw readings are left out. "
            f"At most {MAX_DAYS_PER_DAY_TOOLS} days per call; days without HRV data are left out."
        ),
        annotations=ToolAnnotations(read_only_hint=True),
    )
    async def get_hrv(start_date: StartDate, end_date: EndDate) -> str:
        days = await per_day(
            garmin, start_date, end_date, MAX_DAYS_PER_DAY_TOOLS, lambda g, d: g.get_hrv_data(d), hrv_summary
        )
        return as_json({"start_date": start_date, "end_date": end_date, "count": len(days), "hrv": days})
