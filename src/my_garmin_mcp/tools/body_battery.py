from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from ..garmin import GarminClient
from ..garmin.dates import MAX_DAYS_BODY_BATTERY, parse_range
from ..garmin.extract import body_battery_days
from ._common import EndDate, StartDate, as_json


def register(server: MCPServer, garmin: GarminClient) -> None:
    @server.tool(
        name="get_body_battery",
        title="Body Battery",
        description=(
            "Body Battery (0-100 energy level) per day: highest, lowest, start, end, charged and drained, plus "
            "[local time, level] readings every 2 hours. "
            f"At most {MAX_DAYS_BODY_BATTERY} days per call; days without data are left out."
        ),
        annotations=ToolAnnotations(read_only_hint=True),
    )
    async def get_body_battery(start_date: StartDate, end_date: EndDate) -> str:
        start, end = parse_range(start_date, end_date, MAX_DAYS_BODY_BATTERY)
        payload = await garmin.call(lambda g: g.get_body_battery(start.isoformat(), end.isoformat()))
        days = body_battery_days(payload)
        return as_json({"start_date": start_date, "end_date": end_date, "count": len(days), "body_battery": days})
