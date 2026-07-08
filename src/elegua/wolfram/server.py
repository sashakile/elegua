"""Flask HTTP server for Wolfram kernel evaluation.

Exposes the oracle protocol endpoints that OracleClient expects:
    GET  /health
    POST /evaluate
    POST /evaluate-with-init
    POST /cleanup
    POST /restart
    GET  /check-state

Start with: ``python -m elegua.wolfram serve``
"""

from __future__ import annotations

import atexit
import os
import secrets
import time

from flask import Flask, jsonify, request  # type: ignore[import-untyped]

from elegua.wolfram.kernel import KernelManager

app = Flask(__name__)
km = KernelManager()

# --- Authentication ---
# Accept token from env var; if unset, generate a random one and log it.
_ORACLE_TOKEN: str | None = os.environ.get("ELEGUA_ORACLE_TOKEN")
if _ORACLE_TOKEN is None:
    _ORACLE_TOKEN = secrets.token_urlsafe(32)
    import logging

    logging.getLogger(__name__).warning(
        "No ELEGUA_ORACLE_TOKEN set — generated ephemeral token: %s",
        _ORACLE_TOKEN,
    )
else:
    import logging

    logging.getLogger(__name__).info("Using ELEGUA_ORACLE_TOKEN from environment")


@app.before_request
def _check_auth() -> tuple[tuple | None, int]:  # type: ignore[no-untyped-def]
    """Require Authorization: Bearer <token> on all routes except /health."""
    if request.endpoint == "health":
        return  # type: ignore[return-value]
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and auth[len("Bearer ") :] == _ORACLE_TOKEN:
        return  # type: ignore[return-value]
    return jsonify({"status": "error", "error": "Unauthorized"}), 401


@app.route("/health", methods=["GET"])
def health():  # type: ignore[no-untyped-def]
    """Health check."""
    return jsonify({"status": "ok"})


@app.route("/evaluate", methods=["POST"])
def evaluate():  # type: ignore[no-untyped-def]
    """Evaluate a Wolfram expression without init script."""
    data = request.get_json()
    if not data or "expr" not in data:
        return jsonify({"status": "error", "error": "Missing 'expr' field"}), 400

    expr = data["expr"]
    timeout = int(data.get("timeout", 30))

    start = time.time()
    ok, result, error = km.evaluate(expr, timeout, with_init=False)
    elapsed_ms = int((time.time() - start) * 1000)

    if ok:
        return jsonify({"status": "ok", "result": result, "timing_ms": elapsed_ms})
    status = "timeout" if error and "timed out" in error else "error"
    return jsonify({"status": status, "error": error, "timing_ms": elapsed_ms})


@app.route("/evaluate-with-init", methods=["POST"])
def evaluate_with_init():  # type: ignore[no-untyped-def]
    """Evaluate expression with init script pre-loaded."""
    data = request.get_json()
    if not data or "expr" not in data:
        return jsonify({"status": "error", "error": "Missing 'expr' field"}), 400

    expr = data["expr"]
    timeout = int(data.get("timeout", 60))
    context_id = data.get("context_id")

    start = time.time()
    ok, result, error = km.evaluate(expr, timeout, with_init=True, context_id=context_id)
    elapsed_ms = int((time.time() - start) * 1000)

    if ok:
        return jsonify({"status": "ok", "result": result, "timing_ms": elapsed_ms})
    status = "timeout" if error and "timed out" in error else "error"
    return jsonify({"status": status, "error": error, "timing_ms": elapsed_ms})


@app.route("/cleanup", methods=["POST"])
def cleanup():  # type: ignore[no-untyped-def]
    """Execute configured cleanup expression."""
    ok, result, error = km.cleanup()
    if ok:
        return jsonify({"status": "ok", "result": result})
    return jsonify({"status": "error", "error": error}), 500


@app.route("/restart", methods=["POST"])
def restart():  # type: ignore[no-untyped-def]
    """Hard-restart the Wolfram kernel."""
    try:
        km.restart()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/check-state", methods=["GET"])
def check_state():  # type: ignore[no-untyped-def]
    """Check for leaked symbols after cleanup."""
    is_clean, leaked = km.check_clean_state()
    return jsonify({"clean": is_clean, "leaked": leaked})


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Start the oracle HTTP server."""
    atexit.register(km.stop)
    app.run(host=host, port=port, threaded=True)


def get_oracle_token() -> str:
    """Return the current oracle authentication token.

    This is used by OracleClient to authenticate requests.
    """
    return _ORACLE_TOKEN  # type: ignore[return-value]
