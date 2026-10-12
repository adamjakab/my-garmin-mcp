import json
from typing import Annotated, Any

from pydantic import Field

from ..garmin import GarminClient
from ..garmin.dates import days_in, map_days, parse_range

StartDate = Annotated[str, Field(description="First day, YYYY-MM-DD (inclusive)")]
EndDate = Annotated[
    str,
    Field(description="Last day, YYYY-MM-DD (inclusive, on or after start_date); same as start_date for one day"),
]


async def per_day(garmin: GarminClient, start_date: str, end_date: str, max_days: int, fetch, extract) -> list[dict]:
    """One request per day (`fetch(api, iso_day)`), reduced by `extract(iso_day, payload)`; empty days dropped."""
    start, end = parse_range(start_date, end_date, max_days)

    async def one(day):
        iso = day.isoformat()
        return extract(iso, await garmin.call(lambda g: fetch(g, iso)))

    return [r for r in await map_days(days_in(start, end), one) if r]


def as_json(data: Any) -> str:
    """Compact JSON text. The SDK would pretty-print a returned dict, which more than doubles long number lists."""
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)
