import hashlib
import hmac
import secrets
from collections.abc import Callable


def _digest(value: str) -> bytes:
    return hashlib.sha256(value.encode()).digest()


def access_key_verifier(configured: str | None) -> Callable[[str], bool]:
    """Checks a presented key against the single configured one (MCP_ACCESS_KEY), in constant time."""
    if not configured:
        return lambda _key: False
    expected = _digest(configured)
    return lambda key: hmac.compare_digest(expected, _digest(key))


def generate_key() -> str:
    return "gmcp_" + secrets.token_urlsafe(32)
