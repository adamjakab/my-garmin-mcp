from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from ..garmin import GarminClient
from ..garmin.dates import MAX_DAYS_HEART_RATE, InvalidRequest
from ..garmin.extract import heart_rate_day
from ._common import EndDate, StartDate, as_json, per_day

MIN_BUCKET_MINUTES, MAX_BUCKET_MINUTES = 5, 120


def register(server: MCPServer, garmin: GarminClient) -> None:
    @server.tool(
        name="get_heart_rate",
        title="All-day heart rate",
        description=(
            "All-day heart rate (beats per minute) per day: min, max, resting and average, plus the readings "
            "reduced to [local time, min, max, avg] rows per time bucket (default 30 minutes). "
            f"At most {MAX_DAYS_HEART_RATE} days per call; days without data are left out."
        ),
        annotations=ToolAnnotations(read_only_hint=True),
    )
    async def get_heart_rate(
        start_date: StartDate,
        end_date: EndDate,
        bucket_minutes: Annotated[
            int, Field(description=f"Bucket size in minutes ({MIN_BUCKET_MINUTES}-{MAX_BUCKET_MINUTES}), default 30")
        ] = 30,
    ) -> str:
        if not MIN_BUCKET_MINUTES <= bucket_minutes <= MAX_BUCKET_MINUTES:
            raise InvalidRequest(f"bucket_minutes must be between {MIN_BUCKET_MINUTES} and {MAX_BUCKET_MINUTES}")
        days = await per_day(
            garmin,
            start_date,
            end_date,
            MAX_DAYS_HEART_RATE,
            lambda g, d: g.get_heart_rates(d),
            lambda day, payload: heart_rate_day(day, payload, bucket_minutes),
        )
        return as_json({"start_date": start_date, "end_date": end_date, "count": len(days), "heart_rate": days})
