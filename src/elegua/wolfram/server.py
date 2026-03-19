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

import time

from flask import Flask, jsonify, request  # type: ignore[import-untyped]

from elegua.wolfram.kernel import KernelManager

app = Flask(__name__)
km = KernelManager()


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


def serve(host: str = "0.0.0.0", port: int = 8765) -> None:
    """Start the oracle HTTP server."""
    app.run(host=host, port=port, threaded=True)
