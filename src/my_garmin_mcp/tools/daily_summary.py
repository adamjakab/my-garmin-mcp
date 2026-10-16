from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from ..garmin import GarminClient
from ..garmin.dates import MAX_DAYS_DAILY_SUMMARY
from ..garmin.extract import daily_summary_day
from ._common import EndDate, StartDate, as_json, per_day


def register(server: MCPServer, garmin: GarminClient) -> None:
    @server.tool(
        name="get_daily_summary",
        title="Daily summary (steps, floors, intensity minutes)",
        description=(
            "Daily activity totals per day: steps and step goal, distance (m), floors climbed and floor goal, "
            "moderate and vigorous intensity minutes and goal, total and active calories. "
            f"At most {MAX_DAYS_DAILY_SUMMARY} days per call; days without data are left out."
        ),
        annotations=ToolAnnotations(read_only_hint=True),
    )
    async def get_daily_summary(start_date: StartDate, end_date: EndDate) -> str:
        days = await per_day(
            garmin,
            start_date,
            end_date,
            MAX_DAYS_DAILY_SUMMARY,
            lambda g, d: g.get_user_summary(d),
            daily_summary_day,
        )
        return as_json({"start_date": start_date, "end_date": end_date, "count": len(days), "daily_summary": days})
