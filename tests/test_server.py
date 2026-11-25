"""Exercise the installed CLI over a real loopback HTTP connection."""

import http.client
import json
import os
import shutil
import signal
import socket
import subprocess
import time

import pytest


@pytest.fixture(scope="module")
def server_port():
    executable = shutil.which("nullgate-http-api")
    assert executable, "install the project before running this test"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {**os.environ, "NULLGATE_API_KEY": "local-test-key"}
    process = subprocess.Popen(
        [executable, "--port", str(port)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    try:
        deadline = time.monotonic() + 20
        while True:
            if process.poll() is not None:
                pytest.fail("solver CLI exited before becoming ready")
            try:
                status, _ = request(port, "GET", "/health")
                if status == 200:
                    break
            except OSError:
                pass
            if time.monotonic() >= deadline:
                pytest.fail("solver CLI did not become ready")
            time.sleep(0.1)
        yield port
    finally:
        if process.poll() is None:
            if os.name == "nt":
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                process.send_signal(signal.SIGINT)
        try:
            returncode = process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            pytest.fail("server did not stop gracefully")
        assert returncode == 0
        assert process.stdout is not None
        output = process.stdout.read().decode("utf-8", errors="replace")
        assert f"http://127.0.0.1:{port}" in output
        assert "NULLGATE_API_KEY" in output
        assert "local-test-key" not in output


def request(port, method, path, body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


def test_cli_health(server_port):
    status, body = request(server_port, "GET", "/health")
    assert status == 200
    assert json.loads(body) == {"status": "ok"}


@pytest.mark.parametrize(
    ("headers", "body", "expected_status"),
    [
        ({"Host": "attacker.example"}, b"{}", 400),
        ({"Origin": "https://attacker.example"}, b"{}", 400),
        ({"Content-Type": "text/plain"}, b"{}", 400),
        ({"Content-Type": "application/json"}, b"{", 400),
        ({"Content-Type": "application/json"}, b"[]", 400),
        ({"Content-Type": "application/json"}, b'{"unknown": true}', 400),
        ({"Content-Type": "application/json"}, b" " * (8 * 1024 * 1024 + 1), 413),
    ],
)
def test_cli_rejects_untrusted_requests(server_port, headers, body, expected_status):
    status, response = request(server_port, "POST", "/solve", body, headers)
    assert status == expected_status
    assert json.loads(response)["code"] == "invalid_request"
