from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from ..garmin import GarminClient
from ..garmin.dates import MAX_DAYS_PER_DAY_TOOLS
from ..garmin.extract import training_readiness_day
from ._common import EndDate, StartDate, as_json, per_day


def register(server: MCPServer, garmin: GarminClient) -> None:
    @server.tool(
        name="get_training_readiness",
        title="Training readiness",
        description=(
            "Garmin Training Readiness per day: score (0-100), level, short feedback, local time of the reading "
            "and the contributing factors (sleep, recovery, load, HRV, stress) as percent and feedback; "
            "if there are several readings in a day the latest is used. "
            f"At most {MAX_DAYS_PER_DAY_TOOLS} days per call; days without data are left out."
        ),
        annotations=ToolAnnotations(read_only_hint=True),
    )
    async def get_training_readiness(start_date: StartDate, end_date: EndDate) -> str:
        days = await per_day(
            garmin,
            start_date,
            end_date,
            MAX_DAYS_PER_DAY_TOOLS,
            lambda g, d: g.get_training_readiness(d),
            training_readiness_day,
        )
        return as_json({"start_date": start_date, "end_date": end_date, "count": len(days), "training_readiness": days})
