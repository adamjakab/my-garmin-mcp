import logging

import uvicorn

from .app import create_app
from .auth.keys import access_key_verifier
from .config import load_config
from .garmin import GarminClient


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = load_config()
    if not config.access_key:
        logging.warning(
            "No MCP_ACCESS_KEY configured: every /mcp request will be rejected. "
            "Set MCP_ACCESS_KEY in .env (uv run rotate-key generates one)"
        )
    garmin = GarminClient(config.garmin_email, config.garmin_password, config.garmin_token_store)
    uvicorn.run(create_app(access_key_verifier(config.access_key), garmin), host=config.host, port=config.port)


if __name__ == "__main__":
    main()
