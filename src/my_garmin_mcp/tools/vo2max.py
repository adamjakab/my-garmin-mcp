from typing import Any, cast

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from ..garmin import GarminClient
from ..garmin.dates import MAX_DAYS_SINGLE_REQUEST, parse_range
from ..garmin.extract import vo2max_entries
from ._common import EndDate, StartDate, as_json


def register(server: MCPServer, garmin: GarminClient) -> None:
    @server.tool(
        name="get_vo2max",
        title="VO2 max",
        description=(
            "VO2 max (ml/kg/min) estimates for a date range. `vo2max` is the running/general value, "
            "`vo2max_cycling` is added when Garmin has one. Garmin only records a value on days it re-estimates it "
            "(usually after a qualifying activity), so most days have no entry. "
            f"At most {MAX_DAYS_SINGLE_REQUEST} days per call."
        ),
        annotations=ToolAnnotations(read_only_hint=True),
    )
    async def get_vo2max(start_date: StartDate, end_date: EndDate) -> str:
        start, end = parse_range(start_date, end_date, MAX_DAYS_SINGLE_REQUEST)
        raw = await garmin.call(lambda g: g.get_max_metrics_range(start.isoformat(), end.isoformat()))
        # garminconnect annotates this as a dict, but Garmin returns a list of per-day records.
        payload = cast(list[dict[str, Any]] | None, raw)
        entries = [e for e in vo2max_entries(payload) if start.isoformat() <= e["date"] <= end.isoformat()]
        return as_json({"start_date": start_date, "end_date": end_date, "count": len(entries), "vo2max": entries})
