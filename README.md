<div align="center">
<img src="assets/readme.png" alt="Nullgate" width="100%">

# Nullgate HTTP API

Solve supported protection flows through a local HTTP API.
</div>

## Start

These commands install [uv](https://docs.astral.sh/uv/) and start the API. They do not require Git, Docker, a browser, or a system Python installation.

macOS or Linux:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh && "$HOME/.local/bin/uvx" --python 3.11 --from "nullgate-http-api @ https://github.com/nullgate-club/http-api/archive/refs/heads/main.tar.gz" nullgate-http-api
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"; & "$HOME\.local\bin\uvx.exe" --python 3.11 --from "nullgate-http-api @ https://github.com/nullgate-club/http-api/archive/refs/heads/main.tar.gz" nullgate-http-api
```

Enter your key at the hidden prompt, or set `NULLGATE_API_KEY` before starting. Get a key from the [Nullgate bot](https://t.me/nullgate_app). The server prints its listening URL, the key source, and the supported products. It never prints the key.

The default URL is `http://127.0.0.1:8191`. `GET /health` returns `{"status":"ok"}`. Stop the server with Ctrl+C.

## Solve

Replace the target, user agent, and proxy with your own. Use a session name to reuse your browser identity and cookies.

```sh
curl http://127.0.0.1:8191/solve -H 'Content-Type: application/json' -d '{
  "type": "akamai",
  "url": "https://example.com/",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
  "proxy": "http://user:password@proxy.example:8080",
  "session": "account-1"
}'
```

On Windows PowerShell:

```powershell
$body = '{"type":"akamai","url":"https://example.com/","user_agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36","proxy":"http://user:password@proxy.example:8080","session":"account-1"}'
Invoke-RestMethod http://127.0.0.1:8191/solve -Method Post -ContentType 'application/json' -Body $body
```

Every successful response has the same shape:

```json
{"cookies": [], "result": {"accepted": true}}
```

The actual cookies depend on the target. Each cookie includes `name`, `value`, `domain`, `path`, `secure`, `http_only`, `expires`, `host_only`, and `same_site`.

| `type` | Successful `result` |
|---|---|
| `akamai` | `{"accepted": true}` after the `_abck` cookie reports acceptance. Optional `pixel_iframe` enables the pixel iframe flow. |
| `threatmetrix` | `{"collected": true}` after collection and pagehide complete. Optional `collector` supplies `url`, `org_id`, and `session_id`. |
| `pingone` | `data`, `device_id`, `sdk_version`, and `request_id`. Optional `pingone` accepts `sdk_config`, `jwt_device_attributes`, `jwt_agent_payload`, `client_token`, `token_host`, and `behavioral`. |
| `amazon_acic` | `status` is `PASS`, with the final `url` and `status_code` after challenge verification and continuation. |

You may supply `html` with a target page you already fetched. The solver then does not fetch that page again. Supply `script_url` when the page loads its SDK dynamically. Optional `headers` apply to target requests.

Omit `session` for a one-shot solve. A named session retains cookies and pins its user agent, proxy, and transport. Omitted settings reuse the pinned values. Supply `cookies` to replace that origin's snapshot after external changes. Use the same user agent and proxy for subsequent target requests.

The solver does not run a browser or log in to an application. A successful solve does not guarantee that the target accepts later requests.

## Transport

`transport.emulation` selects a wreq browser profile. When omitted, the solver selects a profile from the user agent. `tls_options` and `http2_options` expose the native wreq settings, and `headers_order` sets the order of ordinary headers. Header names in `headers_order` must be valid and unique, ignoring case. Pseudo headers are not allowed there.

Add this optional context to your request when you need explicit transport settings:

```json
{
  "transport": {
    "emulation": "Chrome154",
    "headers_order": ["user-agent", "accept", "accept-language"],
    "tls_options": {"min_tls_version": "TLS_1_2"},
    "http2_options": {
      "initial_window_size": 1048576,
      "headers_pseudo_order": ["METHOD", "AUTHORITY", "SCHEME", "PATH"]
    }
  }
}
```

Native enum values use their Python names. HTTP2 `headers_stream_dependency`
accepts `{"dependency_id": 0, "weight": 255, "is_exclusive": true}`.
`priorities` accepts up to 128 objects with `stream_id` and a `dependency`
of that same shape. Unknown options fail instead of being ignored.

A JA4 hash alone does not specify TLS settings and cannot reconstruct a ClientHello. Set the underlying browser profile, TLS, HTTP/2, and header order instead. See the upstream [wreq documentation](https://github.com/0x676e67/wreq) for available profiles and native settings.

TLS and HTTP2 option objects replace the corresponding profile configuration,
not individual fields. Keep them omitted to retain the full browser preset.
For an exact custom fingerprint, supply its complete settings.

An error response includes `code`, `message`, `stage`, and `request_id`, with an optional `cause`. Do not automatically retry paid solves.

## SDK clients

The simple clients call this local API: [Python](https://github.com/nullgate-club/nullgate-sdk-py), [TypeScript](https://github.com/nullgate-club/nullgate-sdk-ts), and [Go](https://github.com/nullgate-club/nullgate-sdk-go). The SDKs also provide advanced APIs to prepare protection requests for your own HTTP client.

## Options and boundaries

- `--port`: local port, default `8191`.
- `--base-url`: Nullgate API URL, default `https://api.nullgate.club`.
- `--timeout`: solve timeout in seconds, default `60`, maximum `180`.
- `NULLGATE_API_KEY`: API key, otherwise requested through a hidden prompt.

The server binds only to IPv4 loopback. It accepts JSON bodies up to 8 MiB and rejects foreign `Host` and `Origin` headers. It does not enable CORS. Do not expose the server to untrusted local users.

## Development

Install uv, then run `uv sync` and `make check`. The check runs Ruff, mypy, pytest, and the package build. The tests start the real server without calling a paid API.
