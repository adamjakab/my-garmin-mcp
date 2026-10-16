import socket
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from my_garmin_mcp import __version__
from my_garmin_mcp.app import create_app
from my_garmin_mcp.auth.keys import access_key_verifier, generate_key
from my_garmin_mcp.garmin import GarminClient

KEY = generate_key()


@pytest.fixture(scope="module")
def url():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(access_key_verifier(KEY), GarminClient(None, None, Path("unused"))),
            host="127.0.0.1",
            port=port,
            log_level="warning",
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


def test_access_key_accepts_only_configured_key():
    verify = access_key_verifier(KEY)
    assert verify(KEY)
    assert not verify(generate_key())
    assert not access_key_verifier(None)("anything")


def test_health_is_open(url):
    assert httpx.get(f"{url}/health").json() == {"status": "ok"}


def test_mcp_rejects_missing_or_wrong_key(url):
    assert httpx.post(f"{url}/mcp").status_code == 401
    assert httpx.post(f"{url}/mcp", headers={"Authorization": "Bearer nope"}).status_code == 401


async def test_ping_with_valid_key(url):
    http = httpx.AsyncClient(headers={"Authorization": f"Bearer {KEY}"})
    async with http, Client(streamable_http_client(f"{url}/mcp", http_client=http)) as client:
        tools = await client.list_tools()
        assert sorted(t.name for t in tools.tools) == sorted(
            [
                "ping",
                "get_sleep",
                "get_hrv",
                "get_resting_hr",
                "get_body_battery",
                "get_heart_rate",
                "get_stress",
                "get_training_readiness",
                "get_vo2max",
                "get_weight",
                "get_activities",
                "get_activity",
            ]
        )
        result = await client.call_tool("ping")
        assert result.content[0].text.startswith(f"pong v{__version__} ")
