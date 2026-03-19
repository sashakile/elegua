"""Lightweight echo oracle HTTP server for integration tests.

Implements the oracle protocol endpoints using stdlib only (no Flask).
Echoes back the expression as the result, enabling end-to-end testing
of the HTTP transport without requiring a real compute kernel.

Usage::

    from elegua.testing import EchoOracle

    with EchoOracle() as oracle:
        print(f"Oracle running on {oracle.url}")
        # OracleClient(oracle.url) works against this server
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any


class _EchoHandler(BaseHTTPRequestHandler):
    """Request handler that echoes expressions back as results."""

    server: _EchoHTTPServer  # type: ignore[assignment]

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json_response({"status": "ok"})
        elif self.path == "/check-state":
            self._json_response({"clean": True, "leaked": []})
        else:
            self._json_response({"status": "error", "error": "Not found"}, code=404)

    def do_POST(self) -> None:
        body = self._read_body()

        if self.path in ("/evaluate", "/evaluate-with-init"):
            if not body or "expr" not in body:
                self._json_response({"status": "error", "error": "Missing 'expr' field"}, code=400)
                return
            self._json_response(
                {
                    "status": "ok",
                    "result": body["expr"],
                    "timing_ms": 1,
                }
            )
        elif self.path == "/cleanup":
            self._json_response({"status": "ok", "result": "cleanup-ok"})
        elif self.path == "/restart":
            self._json_response({"status": "ok"})
        else:
            self._json_response({"status": "error", "error": "Not found"}, code=404)

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw)  # type: ignore[no-any-return]

    def _json_response(self, data: dict[str, Any], code: int = 200) -> None:
        payload = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress request logging during tests."""


class _EchoHTTPServer(HTTPServer):
    """HTTPServer subclass that allows port reuse."""

    allow_reuse_address = True


class EchoOracle:
    """Context manager that runs an echo oracle HTTP server in a background thread.

    The server implements the oracle protocol (``/health``, ``/evaluate``,
    ``/evaluate-with-init``, ``/cleanup``, ``/restart``, ``/check-state``)
    by echoing expressions back as results.

    Example::

        with EchoOracle(port=0) as oracle:
            client = OracleClient(oracle.url)
            assert client.health()
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self._host = host
        self._port = port
        self._server: _EchoHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        """Base URL of the running server."""
        if self._server is None:
            msg = "Server not started; use as context manager"
            raise RuntimeError(msg)
        addr = self._server.server_address
        return f"http://{addr[0]}:{addr[1]}"

    def __enter__(self) -> EchoOracle:
        self._server = _EchoHTTPServer((self._host, self._port), _EchoHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
