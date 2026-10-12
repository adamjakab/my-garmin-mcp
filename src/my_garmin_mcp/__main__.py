import logging

import uvicorn

from .app import create_app
from .auth.keys import access_key_verifier
from .config import load_config


def main() -> None:
    config = load_config()
    if not config.access_key:
        logging.warning(
            "No MCP_ACCESS_KEY configured: every /mcp request will be rejected. "
            "Set MCP_ACCESS_KEY in .env (uv run rotate-key generates one)"
        )
    uvicorn.run(create_app(access_key_verifier(config.access_key)), host=config.host, port=config.port)


if __name__ == "__main__":
    main()
