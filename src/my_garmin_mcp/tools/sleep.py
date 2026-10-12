from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from ..garmin import GarminClient
from ..garmin.dates import MAX_DAYS_PER_DAY_TOOLS
from ..garmin.extract import sleep_summary
from ._common import EndDate, StartDate, as_json, per_day


def register(server: MCPServer, garmin: GarminClient) -> None:
    @server.tool(
        name="get_sleep",
        title="Sleep",
        description=(
            "Sleep per night for a date range: sleep score, total duration and the deep/light/REM/awake split "
            "(all durations in seconds), bed and wake time (local), plus overnight heart rate, resting heart rate, "
            "HRV, SpO2, respiration, stress and body battery change. A night is filed under the day you wake up. "
            f"At most {MAX_DAYS_PER_DAY_TOOLS} days per call; days without sleep data are left out."
        ),
        annotations=ToolAnnotations(read_only_hint=True),
    )
    async def get_sleep(start_date: StartDate, end_date: EndDate) -> str:
        nights = await per_day(
            garmin, start_date, end_date, MAX_DAYS_PER_DAY_TOOLS, lambda g, d: g.get_sleep_data(d), sleep_summary
        )
        return as_json({"start_date": start_date, "end_date": end_date, "count": len(nights), "sleep": nights})
