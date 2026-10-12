import json
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from my_garmin_mcp.app import create_app
from my_garmin_mcp.garmin import GarminClient

KEY = "test-key"


class FakeApi:
    """Just enough of garminconnect.Garmin for the tools; counts calls."""

    def __init__(self, *_):
        self.calls: list[str] = []

    def login(self, _store):
        pass

    def get_sleep_data(self, day):
        self.calls.append(f"sleep {day}")
        if day.endswith("-02"):
            return {"dailySleepDTO": {}}
        return {"dailySleepDTO": {"sleepTimeSeconds": 25000, "sleepScores": {"overall": {"value": 80}}}}

    def get_activities_by_date(self, start, end):
        return [{"activityId": 7, "activityName": "Run", "activityType": {"typeKey": "running"}, "distance": 1000.0}]

    def get_activity(self, activity_id):
        if activity_id == "404":
            from garminconnect import GarminConnectNotFoundError

            raise GarminConnectNotFoundError("API Error 404")
        return {
            "activityId": int(activity_id),
            "activityTypeDTO": {"typeKey": "running"},
            "summaryDTO": {"distance": 1000.0},
        }

    def get_activity_weather(self, activity_id):
        return {"temp": 20}

    def get_activity_splits(self, activity_id):
        from garminconnect import GarminConnectConnectionError

        raise GarminConnectConnectionError("boom")


@asynccontextmanager
async def session():
    app = create_app(lambda k: k == KEY, GarminClient("e", "p", Path("/nonexistent"), factory=FakeApi))
    http = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://127.0.0.1:8000",
        headers={"Authorization": f"Bearer {KEY}"},
    )
    async with app.router.lifespan_context(app), http:
        async with Client(streamable_http_client("http://127.0.0.1:8000/mcp", http_client=http)) as client:
            yield client


def _data(result):
    assert not result.is_error, result.content
    return json.loads(result.content[0].text)


async def test_get_sleep_returns_nights_and_skips_empty_days():
    async with session() as client:
        data = _data(await client.call_tool("get_sleep", {"start_date": "2026-10-01", "end_date": "2026-10-03"}))
        assert data["count"] == 2
        assert [n["date"] for n in data["sleep"]] == ["2026-10-01", "2026-10-03"]
        assert data["sleep"][0]["score"] == 80


async def test_bad_range_is_a_tool_error():
    async with session() as client:
        result = await client.call_tool("get_sleep", {"start_date": "2026-10-05", "end_date": "2026-10-01"})
        assert result.is_error and "on or after" in result.content[0].text


async def test_get_activities_is_curated():
    async with session() as client:
        data = _data(await client.call_tool("get_activities", {"start_date": "2026-10-01", "end_date": "2026-10-03"}))
        assert data["activities"] == [{"activity_id": 7, "name": "Run", "distance_m": 1000.0, "type": "running"}]


async def test_get_activity_reports_failed_extras_without_failing():
    async with session() as client:
        data = _data(await client.call_tool("get_activity", {"activity_id": 7, "include": ["weather", "splits"]}))
        assert data["activityId"] == 7 and data["distance"] == 1000.0 and data["activityType"] == {"typeKey": "running"}
        assert data["weather"] == {"temp": 20}
        assert "splits" not in data and "boom" in data["errors"]["splits"]


async def test_get_activity_with_unknown_id_says_so():
    async with session() as client:
        result = await client.call_tool("get_activity", {"activity_id": 404})
        assert result.is_error and "No activity with id 404" in result.content[0].text


async def test_host_header_is_checked_unless_allowed():
    garmin = GarminClient("e", "p", Path("/nonexistent"), factory=FakeApi)
    statuses = []  # response bodies
    for hosts in ((), ("mcp.example.com",)):
        app = create_app(lambda k: True, garmin, hosts)
        async with app.router.lifespan_context(app), httpx.AsyncClient(transport=httpx.ASGITransport(app=app)) as http:
            res = await http.post(
                "http://mcp.example.com/mcp",
                headers={
                    "Authorization": "Bearer x",
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
                content="{}",
            )
        statuses.append(res.text)
    assert "Invalid Host header" in statuses[0]
    assert "Invalid Host header" not in statuses[1]
