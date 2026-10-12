from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from ..garmin import GarminClient
from ..garmin.dates import MAX_DAYS_SINGLE_REQUEST, parse_range
from ..garmin.extract import weight_entries
from ._common import EndDate, StartDate, as_json


def register(server: MCPServer, garmin: GarminClient) -> None:
    @server.tool(
        name="get_weight",
        title="Weight and body composition",
        description=(
            "Weigh-ins for a date range with body composition where the scale provides it: weight_kg, bmi, "
            "body_fat_pct, body_water_pct, muscle_mass_kg, bone_mass_kg, visceral_fat, metabolic_age. "
            f"At most {MAX_DAYS_SINGLE_REQUEST} days per call; an empty list means no weigh-ins in the range."
        ),
        annotations=ToolAnnotations(read_only_hint=True),
    )
    async def get_weight(start_date: StartDate, end_date: EndDate) -> str:
        start, end = parse_range(start_date, end_date, MAX_DAYS_SINGLE_REQUEST)
        payload = await garmin.call(lambda g: g.get_body_composition(start.isoformat(), end.isoformat()))
        entries = weight_entries(payload)
        return as_json({"start_date": start_date, "end_date": end_date, "count": len(entries), "weight": entries})
