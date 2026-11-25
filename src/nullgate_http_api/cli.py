"""Start the local HTTP API with a user-supplied Nullgate API key."""

import argparse
import math
import os
import signal
import sys
from getpass import getpass
from types import FrameType
from typing import NoReturn

from aiohttp import web
from nullgate import NullgateError
from nullgate.solver.engine import Engine
from nullgate.solver.models import SolveError

from .app import create_app


def _interrupt(signum: int, frame: FrameType | None) -> NoReturn:
    raise KeyboardInterrupt


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Nullgate HTTP API.")
    parser.add_argument("--port", type=int, default=8191)
    parser.add_argument("--base-url", default="https://api.nullgate.club")
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= 180:
        parser.error("--timeout must be positive and at most 180 seconds")
    api_key = os.environ.get("NULLGATE_API_KEY")
    key_source = "NULLGATE_API_KEY environment variable" if api_key else "hidden prompt"
    if not api_key:
        try:
            api_key = getpass(
                "Nullgate API key (get one at https://t.me/nullgate_app): "
            )
        except (EOFError, KeyboardInterrupt):
            print("API key is required.", file=sys.stderr)
            raise SystemExit(1) from None
    if not api_key:
        print("API key is required.", file=sys.stderr)
        raise SystemExit(1)
    try:
        solver = Engine(api_key, base_url=args.base_url, timeout=args.timeout)
    except (SolveError, NullgateError):
        parser.error("Invalid API key or API URL")
    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, _interrupt)

    def announce(_: str) -> None:
        print(
            f"Nullgate HTTP API listening at http://127.0.0.1:{args.port}\n"
            f"API key source: {key_source}\n"
            "Products: Akamai, ThreatMetrix, PingOne Protect, Amazon ACIC\n"
            "Get an API key: https://t.me/nullgate_app\n"
            "Press Ctrl+C to stop.",
            flush=True,
        )

    web.run_app(
        create_app(solver, args.port),
        host="127.0.0.1",
        port=args.port,
        access_log=None,
        shutdown_timeout=args.timeout + 5,
        handler_cancellation=True,
        print=announce,
    )


if __name__ == "__main__":
    main()
