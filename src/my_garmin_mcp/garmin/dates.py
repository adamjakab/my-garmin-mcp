import asyncio
from collections.abc import Awaitable, Callable
from datetime import date, timedelta

from mcp.server.mcpserver.exceptions import ToolError

# Per-day tools make one Garmin request per day, so keep ranges and parallelism modest.
MAX_DAYS_PER_DAY_TOOLS = 31
MAX_DAYS_SINGLE_REQUEST = 366
MAX_DAYS_ACTIVITIES = 92
CONCURRENCY = 3


class InvalidRequest(ToolError):
    """The caller passed something unusable (bad date, range too long, unknown id): shown to Claude as is."""


def parse_date(value: str, name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise InvalidRequest(f"{name} must be a date in YYYY-MM-DD format, got {value!r}") from None


def parse_range(start_date: str, end_date: str, max_days: int) -> tuple[date, date]:
    start, end = parse_date(start_date, "start_date"), parse_date(end_date, "end_date")
    if end < start:
        raise InvalidRequest("end_date must be on or after start_date")
    days = (end - start).days + 1
    if days > max_days:
        raise InvalidRequest(f"The range is {days} days; at most {max_days} days are allowed per call. Split it up.")
    return start, end


def days_in(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


async def map_days[T](days: list[date], fn: Callable[[date], Awaitable[T]]) -> list[T]:
    """Run fn for every day, at most CONCURRENCY at a time, keeping the order."""
    gate = asyncio.Semaphore(CONCURRENCY)

    async def one(day: date) -> T:
        async with gate:
            return await fn(day)

    return await asyncio.gather(*(one(d) for d in days))
