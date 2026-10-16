from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from ..garmin import GarminClient
from ..garmin.dates import MAX_DAYS_RESPIRATION
from ..garmin.extract import respiration_day
from ._common import EndDate, StartDate, as_json, per_day


def register(server: MCPServer, garmin: GarminClient) -> None:
    @server.tool(
        name="get_respiration",
        title="Respiration",
        description=(
            "All-day respiration (breaths per minute) per day: lowest, highest, waking average and sleep average, "
            "plus [local time, value] readings per 30-minute bucket. "
            "For just the night's respiration see get_sleep. "
            f"At most {MAX_DAYS_RESPIRATION} days per call; days without data are left out."
        ),
        annotations=ToolAnnotations(read_only_hint=True),
    )
    async def get_respiration(start_date: StartDate, end_date: EndDate) -> str:
        days = await per_day(
            garmin,
            start_date,
            end_date,
            MAX_DAYS_RESPIRATION,
            lambda g, d: g.get_respiration_data(d),
            respiration_day,
        )
        return as_json({"start_date": start_date, "end_date": end_date, "count": len(days), "respiration": days})
