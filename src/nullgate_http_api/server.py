"""Local HTTP interface for the optional solver."""

import argparse
import json
import math
import os
import signal
import sys
from collections.abc import Awaitable, Callable
from getpass import getpass
from types import FrameType
from typing import NoReturn
from urllib.parse import urlsplit
from uuid import uuid4

from aiohttp import web
from nullgate import NullgateError
from nullgate.solver import Solver
from nullgate.solver.models import SolveError

_MAX_BODY = 1024 * 1024
_STATUS = {
    "invalid_request": 400,
    "session_conflict": 409,
    "session_not_found": 409,
    "busy": 429,
    "session_capacity": 429,
    "timeout": 504,
    "target_error": 502,
    "transport_error": 502,
    "solve_failed": 502,
    "protection_not_found": 502,
}


def _error(code: str, message: str, stage: str, status: int) -> web.Response:
    return web.json_response(
        {"code": code, "message": message, "stage": stage, "request_id": str(uuid4())},
        status=status,
    )


def _local_authority(value: str, port: int) -> bool:
    return value.lower() in {f"127.0.0.1:{port}", f"localhost:{port}"}


def _trusted_request(request: web.Request, port: int) -> bool:
    hosts = request.headers.getall("Host", [])
    if len(hosts) != 1 or not _local_authority(hosts[0], port):
        return False
    origins = request.headers.getall("Origin", [])
    if not origins:
        return True
    if len(origins) != 1:
        return False
    origin = origins[0]
    try:
        parsed = urlsplit(origin)
        return (
            parsed.scheme == "http"
            and parsed.netloc.lower() == hosts[0].lower()
            and not parsed.path
            and not parsed.query
            and not parsed.fragment
            and origin.lower() == f"http://{hosts[0].lower()}"
        )
    except ValueError:
        return False


def create_app(solver: Solver, port: int) -> web.Application:
    @web.middleware
    async def boundary(
        request: web.Request,
        handler: Callable[[web.Request], Awaitable[web.StreamResponse]],
    ) -> web.StreamResponse:
        if not _trusted_request(request, port):
            return _error("invalid_request", "Invalid Host or Origin.", "request", 400)
        return await handler(request)

    async def health(request: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    async def solve(request: web.Request) -> web.Response:
        if request.content_type != "application/json":
            return _error(
                "invalid_request", "Expected application/json.", "request", 400
            )
        try:
            body = await request.read()
            payload = json.loads(body.decode("utf-8"))
        except web.HTTPRequestEntityTooLarge:
            return _error(
                "invalid_request", "Request body exceeds 1 MiB.", "request", 413
            )
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _error("invalid_request", "Invalid JSON body.", "request", 400)
        if not isinstance(payload, dict):
            return _error("invalid_request", "Expected a JSON object.", "request", 400)
        try:
            cookies = await solver.solve(**payload)
        except SolveError as exc:
            status = getattr(exc, "status", None)
            if status not in (401, 402):
                status = _STATUS.get(exc.code, 502)
            error = {
                "code": exc.code,
                "message": exc.message,
                "stage": exc.stage,
                "request_id": exc.request_id or str(uuid4()),
            }
            if exc.cause is not None:
                error["cause"] = exc.cause
            return web.json_response(error, status=status)
        except Exception:
            return _error("solve_failed", "Solver failed.", "solve", 502)
        return web.json_response(cookies)

    async def close_solver(app: web.Application) -> None:
        await solver.aclose()

    app = web.Application(client_max_size=_MAX_BODY, middlewares=[boundary])
    app.router.add_get("/health", health)
    app.router.add_post("/solve", solve)
    app.on_cleanup.append(close_solver)
    return app


def _interrupt(signum: int, frame: FrameType | None) -> NoReturn:
    raise KeyboardInterrupt


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Nullgate solver.")
    parser.add_argument("--port", type=int, default=8191)
    parser.add_argument("--base-url", default="https://api.nullgate.club")
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= 180:
        parser.error("--timeout must be positive and at most 180 seconds")
    api_key = os.environ.get("NULLGATE_API_KEY")
    if not api_key:
        try:
            api_key = getpass("Nullgate API key: ")
        except (EOFError, KeyboardInterrupt):
            print("API key is required.", file=sys.stderr)
            raise SystemExit(1) from None
    if not api_key:
        print("API key is required.", file=sys.stderr)
        raise SystemExit(1)
    try:
        solver = Solver(api_key, base_url=args.base_url, timeout=args.timeout)
    except (SolveError, NullgateError):
        parser.error("Invalid API key or API URL")
    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, _interrupt)
    web.run_app(
        create_app(solver, args.port),
        host="127.0.0.1",
        port=args.port,
        access_log=None,
        shutdown_timeout=args.timeout + 5,
    )


if __name__ == "__main__":
    main()
