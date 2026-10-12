import argparse
import os
import re
import sys
from pathlib import Path

from .keys import generate_key

ENV_FILE = Path(".env")
VAR = "MCP_ACCESS_KEY"


def main() -> None:
    parser = argparse.ArgumentParser(description=f"Write a new {VAR} into {ENV_FILE}.")
    parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    args = parser.parse_args()

    if not ENV_FILE.exists():
        sys.exit(f"No {ENV_FILE} here. Copy .env.example to .env first.")

    if not args.yes:
        if not sys.stdin.isatty():
            sys.exit("Not interactive: pass --yes to rotate without asking.")
        print(f"WARNING: this replaces {VAR} in {ENV_FILE}. The current key stops working once the server restarts,")
        print("and every client using it (Claude Code, the phone, ...) must be updated with the new key.")
        if input("Rotate the key? [y/N] ").strip().lower() not in {"y", "yes"}:
            print("Cancelled; nothing changed.")
            return

    key = generate_key()
    text = ENV_FILE.read_text()
    line = re.compile(rf"^{VAR}=.*$", re.MULTILINE)
    updated = line.sub(lambda _: f"{VAR}={key}", text) if line.search(text) else text.rstrip("\n") + f"\n{VAR}={key}\n"

    tmp = ENV_FILE.with_suffix(".tmp")
    tmp.write_text(updated)
    tmp.chmod(ENV_FILE.stat().st_mode)
    os.replace(tmp, ENV_FILE)

    print(f"Updated {VAR} in {ENV_FILE}. New key:\n\n{key}\n")
    print("Restart the service to apply it:  pm2 restart my-garmin-mcp")
