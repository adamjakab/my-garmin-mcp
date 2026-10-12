import socket
import threading
import time

import httpx
import pytest
import uvicorn
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from my_garmin_mcp.app import create_app
from my_garmin_mcp.auth.keys import access_key_verifier, generate_key

KEY = generate_key()


@pytest.fixture(scope="module")
def url():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(create_app(access_key_verifier(KEY)), host="127.0.0.1", port=port, log_level="warning")
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
        assert [t.name for t in tools.tools] == ["ping"]
        result = await client.call_tool("ping")
        assert "pong" in result.content[0].text
