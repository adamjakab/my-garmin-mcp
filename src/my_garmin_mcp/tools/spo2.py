from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from ..garmin import GarminClient
from ..garmin.dates import MAX_DAYS_SPO2
from ..garmin.extract import spo2_day
from ._common import EndDate, StartDate, as_json, per_day


def register(server: MCPServer, garmin: GarminClient) -> None:
    @server.tool(
        name="get_spo2",
        title="Blood oxygen (SpO2)",
        description=(
            "All-day blood oxygen (SpO2, %) per day: average, lowest, latest and sleep average, "
            "plus [local time, value] readings per 60-minute bucket. "
            "For just the night's SpO2 see get_sleep. "
            f"At most {MAX_DAYS_SPO2} days per call; days without data are left out."
        ),
        annotations=ToolAnnotations(read_only_hint=True),
    )
    async def get_spo2(start_date: StartDate, end_date: EndDate) -> str:
        days = await per_day(
            garmin,
            start_date,
            end_date,
            MAX_DAYS_SPO2,
            lambda g, d: g.get_spo2_data(d),
            spo2_day,
        )
        return as_json({"start_date": start_date, "end_date": end_date, "count": len(days), "spo2": days})
