import asyncio
from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from ..garmin import GarminClient, GarminError
from ..garmin.dates import InvalidRequest
from ..garmin.extract import bucket_details, flatten_activity
from ._common import as_json

Extra = Literal[
    "details",
    "splits",
    "typed_splits",
    "split_summaries",
    "exercise_sets",
    "hr_zones",
    "power_zones",
    "weather",
    "gear",
]

_FETCH = {
    "details": lambda g, i: g.get_activity_details(i),
    "splits": lambda g, i: g.get_activity_splits(i),
    "typed_splits": lambda g, i: g.get_activity_typed_splits(i),
    "split_summaries": lambda g, i: g.get_activity_split_summaries(i),
    "exercise_sets": lambda g, i: g.get_activity_exercise_sets(i),
    "hr_zones": lambda g, i: g.get_activity_hr_in_timezones(i),
    "power_zones": lambda g, i: g.get_activity_power_in_timezones(i),
    "weather": lambda g, i: g.get_activity_weather(i),
    "gear": lambda g, i: g.get_activity_gear(i),
}


def register(server: MCPServer, garmin: GarminClient) -> None:
    @server.tool(
        name="get_activity",
        title="Activity detail",
        description=(
            "One activity by id (from get_activities): the full summary, and optionally extra data via `include`: "
            "details (heart rate, speed, power, cadence, elevation... as rows of "
            "[seconds_since_start, min, max, avg, count] per time bucket, 60 s by default; see bucket_seconds), "
            "splits, typed_splits, split_summaries, exercise_sets (strength workouts), hr_zones, power_zones "
            "(time in zone), weather, gear. Each extra makes the answer bigger, so ask only for what is needed. "
            "An extra that fails is reported under `errors` without failing the whole call."
        ),
        annotations=ToolAnnotations(read_only_hint=True),
    )
    async def get_activity(
        activity_id: Annotated[int, Field(gt=0, description="Garmin activity id")],
        include: Annotated[list[Extra] | None, Field(description="Extra data to add; default none")] = None,
        bucket_seconds: Annotated[
            int,
            Field(ge=10, le=3600, description="Bucket size for `details`; raise it (e.g. 300) for a smaller answer"),
        ] = 60,
    ) -> str:
        aid = str(activity_id)
        summary = await garmin.call(lambda g: g.get_activity(aid))
        if not summary:
            raise InvalidRequest(f"No activity with id {activity_id}")
        result = flatten_activity(summary)
        errors: dict[str, str] = {}

        async def fetch(name: str) -> None:
            try:
                data = await garmin.call(lambda g: _FETCH[name](g, aid))
            except GarminError as e:
                errors[name] = str(e)
                return
            result[name] = bucket_details(data, bucket_seconds) if name == "details" else data

        await asyncio.gather(*(fetch(n) for n in dict.fromkeys(include or [])))
        if errors:
            result["errors"] = errors
        return as_json(result)
