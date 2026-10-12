from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from ..garmin import GarminClient
from ..garmin.dates import MAX_DAYS_ACTIVITIES, parse_range
from ..garmin.extract import activity_list_item
from ._common import EndDate, StartDate, as_json


def register(server: MCPServer, garmin: GarminClient) -> None:
    @server.tool(
        name="get_activities",
        title="Activities",
        description=(
            "List the recorded activities (runs, rides, workouts, ...) in a date range with their key numbers: "
            "type, start time (local), distance in metres, duration in seconds, elevation gain, speed, heart rate, "
            "power, cadence, calories, training effect and load. Use `activity_id` with get_activity for the "
            f"full detail of one. At most {MAX_DAYS_ACTIVITIES} days per call."
        ),
        annotations=ToolAnnotations(read_only_hint=True),
    )
    async def get_activities(start_date: StartDate, end_date: EndDate) -> str:
        start, end = parse_range(start_date, end_date, MAX_DAYS_ACTIVITIES)
        payload = await garmin.call(lambda g: g.get_activities_by_date(start.isoformat(), end.isoformat()))
        items = [activity_list_item(a) for a in payload or []]
        return as_json({"start_date": start_date, "end_date": end_date, "count": len(items), "activities": items})
