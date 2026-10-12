import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Real environment variables win over the file.
load_dotenv(override=False)


@dataclass(frozen=True)
class Config:
    port: int
    host: str
    access_key: str | None
    data_dir: Path
    garmin_email: str | None
    garmin_password: str | None
    garmin_token_store: Path


def load_config() -> Config:
    env = os.environ
    return Config(
        port=int(env.get("PORT", "3334")),
        host=env.get("HOST", "127.0.0.1"),
        access_key=env.get("MCP_ACCESS_KEY") or None,
        data_dir=Path(env.get("DATA_DIR", "data")).resolve(),
        garmin_email=env.get("GARMIN_EMAIL"),
        garmin_password=env.get("GARMIN_PASSWORD"),
        garmin_token_store=Path(env.get("GARMIN_TOKEN_STORE", "data/garmin-tokens")).resolve(),
    )
