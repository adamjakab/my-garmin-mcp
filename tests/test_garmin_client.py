from pathlib import Path

import pytest
from garminconnect import GarminConnectAuthenticationError, GarminConnectTooManyRequestsError

from my_garmin_mcp.garmin import GarminClient, GarminError
from my_garmin_mcp.garmin.client import LOGIN_COOLDOWN_SECONDS


class FakeGarmin:
    """Stands in for garminconnect.Garmin; `behaviour` decides what login() and calls do."""

    instances: list["FakeGarmin"] = []

    def __init__(self, email, password, login_error=None):
        self.login_error = login_error
        self.logged_in = False
        self.rejected_once = False
        FakeGarmin.instances.append(self)

    def login(self, store):
        if self.login_error:
            raise self.login_error
        self.logged_in = True

    def data(self):
        return {"ok": True}


class Clock:
    now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture(autouse=True)
def _reset():
    FakeGarmin.instances.clear()


def make(factory=FakeGarmin, clock=None, email="a@b.c", password="pw"):
    return GarminClient(email, password, Path("/nonexistent"), factory=factory, clock=clock or Clock())


async def test_logs_in_once_and_reuses_the_session():
    client = make()
    for _ in range(5):
        assert await client.call(lambda g: g.data()) == {"ok": True}
    assert client.login_count == 1
    assert len(FakeGarmin.instances) == 1


async def test_failed_login_is_not_retried_during_cooldown():
    clock = Clock()
    client = make(
        factory=lambda e, p: FakeGarmin(e, p, login_error=GarminConnectTooManyRequestsError("429")), clock=clock
    )
    with pytest.raises(GarminError, match="rate limiting"):
        await client.call(lambda g: g.data())
    with pytest.raises(GarminError, match="paused"):
        await client.call(lambda g: g.data())
    assert client.login_count == 1
    clock.now += LOGIN_COOLDOWN_SECONDS + 1
    with pytest.raises(GarminError, match="rate limiting"):
        await client.call(lambda g: g.data())
    assert client.login_count == 2


async def test_rejected_session_is_replaced_once():
    client = make()
    calls = {"n": 0}

    def flaky(g):
        calls["n"] += 1
        if calls["n"] == 1:
            raise GarminConnectAuthenticationError("expired")
        return "fine"

    assert await client.call(flaky) == "fine"
    assert client.login_count == 2


async def test_api_errors_become_garmin_errors():
    client = make()

    def boom(g):
        raise ValueError("bad day")

    with pytest.raises(GarminError, match="ValueError: bad day"):
        await client.call(boom)


async def test_no_credentials_and_no_tokens():
    with pytest.raises(GarminError, match="No Garmin tokens"):
        await make(email=None, password=None).call(lambda g: g.data())


def _token_store(tmp_path):
    (tmp_path / "garmin_tokens.json").write_text("{}")
    return tmp_path


def _always_rejected(g):
    raise GarminConnectAuthenticationError("expired")


async def test_tokens_are_deleted_after_repeated_rejections(tmp_path, caplog):
    store = _token_store(tmp_path)
    client = GarminClient("a@b.c", "pw", store, factory=FakeGarmin, clock=Clock())
    with caplog.at_level("WARNING"), pytest.raises(GarminError):
        await client.call(_always_rejected)  # two rejections: tokens stay
    assert (store / "garmin_tokens.json").exists()
    with pytest.raises(GarminError):
        await client.call(_always_rejected)  # third rejection: tokens go
    assert not (store / "garmin_tokens.json").exists()
    assert "deleted" in caplog.text and "garmin_tokens.json" in caplog.text


async def test_success_resets_the_failure_count(tmp_path):
    store = _token_store(tmp_path)
    client = GarminClient("a@b.c", "pw", store, factory=FakeGarmin, clock=Clock())
    state = {"n": 0}

    def reject_once_then_work(g):
        state["n"] += 1
        if state["n"] % 2 == 1:
            raise GarminConnectAuthenticationError("expired")
        return "ok"

    for _ in range(5):  # each call is rejected once, then succeeds: never 3 in a row
        assert await client.call(reject_once_then_work) == "ok"
    assert (store / "garmin_tokens.json").exists()


async def test_tokens_are_kept_without_credentials(tmp_path, caplog):
    store = _token_store(tmp_path)
    client = GarminClient(None, None, store, factory=FakeGarmin, clock=Clock())
    with caplog.at_level("ERROR"):
        for _ in range(2):
            with pytest.raises(GarminError):
                await client.call(_always_rejected)
    assert (store / "garmin_tokens.json").exists()
    assert "no credentials are configured" in caplog.text
