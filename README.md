# Nullgate HTTP API

Run a local HTTP server that uses the [Nullgate Python SDK](https://github.com/nullgate-club/nullgate-sdk-py) to solve Akamai and ThreatMetrix pages. You supply your own API key, user agent, and optional proxy.

## Start

These commands install [uv](https://docs.astral.sh/uv/) and launch the prototype. They do not require Git, Docker, a browser, or a system Python installation. Enter your API key at the hidden prompt, or set `NULLGATE_API_KEY` in your environment before starting.

macOS or Linux:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh && "$HOME/.local/bin/uvx" --python 3.11 --from "nullgate-http-api @ https://github.com/nullgate-club/http-api/archive/refs/heads/feat/prototype.tar.gz" nullgate-http-api
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"; & "$HOME\.local\bin\uvx.exe" --python 3.11 --from "nullgate-http-api @ https://github.com/nullgate-club/http-api/archive/refs/heads/feat/prototype.tar.gz" nullgate-http-api
```

The server listens on `http://127.0.0.1:8191`. `GET /health` returns `{"status":"ok"}`. Stop the server with Ctrl+C.

## Solve

Send JSON to `POST /solve`. For example, replace the URL and user agent with your own:

```sh
curl http://127.0.0.1:8191/solve -H 'Content-Type: application/json' -d '{"type":"akamai","url":"https://example.com/","user_agent":"your user agent"}'
```

In Windows PowerShell, send the same request with its native HTTP command:

```powershell
Invoke-RestMethod http://127.0.0.1:8191/solve -Method Post -ContentType 'application/json' -Body '{"type":"akamai","url":"https://example.com/","user_agent":"your user agent"}'
```

A successful response is a JSON array of cookies. An error response contains `code`, `message`, `stage`, and `request_id`, with an optional `cause`.

Set `proxy` to use your own proxy. Use the same user agent and IP address for subsequent requests to the target. An optional `session` name retains cookies between solves. Supply `cookies` to replace the session's cookie snapshot when it changes externally. Omit `session` for a one-shot solve. ThreatMetrix requests use `type: "threatmetrix"` and can supply `collector` with `url`, `org_id`, and `session_id` when needed.

The server does not run a browser. A successful solve does not guarantee that a target accepts later requests. See the [SDK](https://github.com/nullgate-club/nullgate-sdk-py) for solver options and usage.

## Options and boundaries

- `--port`: local port, default `8191`.
- `--base-url`: Nullgate API URL, default `https://api.nullgate.club`.
- `--timeout`: solve timeout in seconds, default `60`.
- `NULLGATE_API_KEY`: API key, otherwise requested through a hidden prompt.

The server binds only to IPv4 loopback. It accepts JSON bodies up to 1 MiB and rejects foreign `Host` and `Origin` headers. It does not enable CORS. Do not expose the server to untrusted local users.

## Development

Install uv, then run `uv sync` and `make check`. The check runs Ruff, mypy, pytest, and the package build. The tests start the real server without calling a paid API.
