import asyncio
import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectNotFoundError,
    GarminConnectTooManyRequestsError,
)
from mcp.server.mcpserver.exceptions import ToolError

log = logging.getLogger(__name__)
T = TypeVar("T")

# After a failed credential login, do not try again for this long. Repeated logins from one IP are
# what makes Garmin block the account, so a failure must never turn into a retry storm.
LOGIN_COOLDOWN_SECONDS = 15 * 60

# After this many rejected calls in a row (no success in between) the saved tokens are considered dead:
# the token file is deleted so the next login starts fresh from the credentials.
MAX_AUTH_FAILURES = 3


class GarminError(ToolError):
    """A Garmin failure with a message that is safe to show to Claude (never contains credentials).

    A ToolError, so the MCP server returns the message as a tool error instead of hiding it as a crash.
    """


class GarminNotFound(GarminError):
    """Garmin answered 404: the requested resource (e.g. an activity id) does not exist."""


class GarminClient:
    """One shared, lazily created Garmin session for the whole process.

    - Tokens live in `token_store` (a directory holding garmin_tokens.json). A login first restores them
      and refreshes them when they are about to expire; the credentials are used only when that fails.
    - Logins are serialised and rate limited (see LOGIN_COOLDOWN_SECONDS), so concurrent tool calls share
      one login and a failed login is not retried in a loop.
    - The library is blocking, so every call runs in a worker thread.
    """

    def __init__(
        self,
        email: str | None,
        password: str | None,
        token_store: Path,
        *,
        factory: Callable[[str | None, str | None], Garmin] = lambda e, p: Garmin(e, p),
        clock: Callable[[], float] = time.monotonic,
    ):
        self._email = email
        self._password = password
        self._token_store = token_store
        self._factory = factory
        self._clock = clock
        self._api: Garmin | None = None
        self._lock = threading.Lock()
        self._blocked_until = 0.0
        self._last_failure = ""
        self._auth_failures = 0
        self.login_count = 0

    def _login(self) -> Garmin:
        """Return the shared session, logging in if there is none. Caller holds no lock."""
        with self._lock:
            if self._api is not None:
                return self._api
            now = self._clock()
            if now < self._blocked_until:
                wait = int(self._blocked_until - now) // 60 + 1
                raise GarminError(f"Garmin login is paused for about {wait} more minute(s) after: {self._last_failure}")
            if not (self._email and self._password) and not (self._token_store / "garmin_tokens.json").exists():
                raise GarminError("No Garmin tokens and no GARMIN_EMAIL/GARMIN_PASSWORD configured")
            api = self._factory(self._email, self._password)
            try:
                self.login_count += 1
                api.login(str(self._token_store))
            except Exception as e:
                self._last_failure = _describe(e)
                self._blocked_until = self._clock() + LOGIN_COOLDOWN_SECONDS
                log.warning("Garmin login failed: %s", self._last_failure)
                raise GarminError(f"Garmin login failed: {self._last_failure}") from e
            self._api = api
            return api

    def _drop_session(self, failed: Garmin) -> None:
        with self._lock:
            if self._api is failed:
                self._api = None

    def _record_auth_failure(self) -> None:
        """Count a rejected call; at MAX_AUTH_FAILURES in a row, delete the saved tokens so the next login is fresh."""
        with self._lock:
            self._auth_failures += 1
            failures = self._auth_failures
            if failures < MAX_AUTH_FAILURES:
                log.warning("Garmin rejected the session (%d/%d in a row)", failures, MAX_AUTH_FAILURES)
                return
            self._auth_failures = 0
            token_file = self._token_store / "garmin_tokens.json"
            if not (self._email and self._password):
                log.error(
                    "Garmin rejected the session %d times in a row, but no credentials are configured: keeping %s",
                    failures,
                    token_file,
                )
                return
            try:
                token_file.unlink(missing_ok=True)
            except OSError as e:
                log.error("Could not delete the rejected token file %s: %s", token_file, e)
                return
            log.warning(
                "Garmin rejected the session %d times in a row: deleted %s, the next request logs in again",
                failures,
                token_file,
            )

    def _call_sync(self, fn: Callable[[Garmin], T]) -> T:
        api = self._login()
        try:
            result = fn(api)
        except GarminConnectAuthenticationError:
            # The session was rejected: drop it and retry once. The login restores/refreshes the saved
            # tokens first and only falls back to the credentials if they are really dead.
            self._record_auth_failure()
            self._drop_session(api)
            api = self._login()
            try:
                result = fn(api)
            except GarminConnectAuthenticationError as e:
                self._record_auth_failure()
                raise GarminError(f"Garmin request failed: {_describe(e)}") from e
            except Exception as e:
                raise _request_error(e) from e
        except GarminError:
            raise
        except Exception as e:
            raise _request_error(e) from e
        with self._lock:
            self._auth_failures = 0
        return result

    async def call(self, fn: Callable[[Garmin], T]) -> T:
        """Run `fn(api)` against the shared session in a worker thread, e.g. `call(lambda g: g.get_sleep_data(day))`."""
        return await asyncio.to_thread(self._call_sync, fn)


def _request_error(e: Exception) -> GarminError:
    if isinstance(e, GarminConnectNotFoundError):
        return GarminNotFound("Garmin request failed: not found (HTTP 404)")
    return GarminError(f"Garmin request failed: {_describe(e)}")


def _describe(e: Exception) -> str:
    if isinstance(e, GarminConnectTooManyRequestsError):
        return "Garmin is rate limiting this account/IP (HTTP 429); wait before retrying"
    if isinstance(e, GarminConnectAuthenticationError):
        return f"authentication was rejected ({e})"
    if isinstance(e, GarminConnectConnectionError):
        return f"connection problem ({e})"
    return f"{type(e).__name__}: {e}"
