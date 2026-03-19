"""HTTP client for the Wolfram oracle server.

Uses stdlib urllib — no external HTTP dependency required.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class OracleClient:
    """Client for the Wolfram oracle HTTP server."""

    def __init__(self, base_url: str = "http://localhost:8765") -> None:
        self.base_url = base_url.rstrip("/")

    def health(self) -> bool:
        """Check if the oracle server is healthy."""
        try:
            data = self._get("/health", timeout=5)
            return data.get("status") == "ok"
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def health_or_raise(self) -> None:
        """Check health, raising on failure with the original cause."""
        try:
            data = self._get("/health", timeout=5)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise RuntimeError(f"Oracle unavailable: {exc}") from exc
        if data.get("status") != "ok":
            raise RuntimeError(f"Oracle unhealthy (status={data.get('status')!r})")

    def evaluate_with_xact(
        self,
        expr: str,
        timeout: int = 60,
        context_id: str | None = None,
    ) -> dict[str, Any]:
        """Evaluate a Wolfram expression with xAct pre-loaded."""
        body: dict[str, Any] = {"expr": expr, "timeout": timeout}
        if context_id:
            body["context_id"] = context_id
        try:
            return self._post("/evaluate-with-init", body, timeout=timeout + 5)
        except (urllib.error.URLError, OSError) as exc:
            return {"status": "error", "error": str(exc)}

    def cleanup(self) -> bool:
        """Clear Global context and reset xAct registries."""
        try:
            data = self._post("/cleanup", {}, timeout=35)
            return data.get("status") == "ok"
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def check_clean_state(self) -> tuple[bool, list[str]]:
        """Query registry counts for leak detection."""
        try:
            data = self._get("/check-state", timeout=15)
            return data.get("clean", False), data.get("leaked", [])
        except (urllib.error.URLError, OSError, ValueError):
            return False, []

    def _get(self, path: str, timeout: int) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read())  # type: ignore[no-any-return]

    def _post(self, path: str, body: dict[str, Any], timeout: int) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())  # type: ignore[no-any-return]
