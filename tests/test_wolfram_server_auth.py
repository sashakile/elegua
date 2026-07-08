"""Tests for Wolfram oracle server authentication (elegua-b3sl)."""

from __future__ import annotations

import json
import os
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest

flask = pytest.importorskip("flask")


@pytest.fixture(autouse=True)
def _clear_env_token() -> Any:
    """Remove ELEGUA_ORACLE_TOKEN before each test so we get a clean slate."""
    old = os.environ.pop("ELEGUA_ORACLE_TOKEN", None)
    yield
    if old is not None:
        os.environ["ELEGUA_ORACLE_TOKEN"] = old


def _make_app(token: str = "test-token-123") -> Any:
    """Create a fresh Flask test app with the given token configured."""
    os.environ["ELEGUA_ORACLE_TOKEN"] = token

    # Force a clean reload of the server module so it reads the env var
    for mod_name in list(sys.modules.keys()):
        if "elegua.wolfram.server" in mod_name:
            del sys.modules[mod_name]

    import elegua.wolfram.server  # type: ignore[import-untyped]

    # Replace the KernelManager with a mock
    km = MagicMock()
    km.evaluate.return_value = (True, "42", None)
    elegua.wolfram.server.km = km

    return elegua.wolfram.server.app


@pytest.fixture
def app() -> Any:
    return _make_app()


@pytest.fixture
def client(app: Any) -> Any:
    return app.test_client()


class TestServerAuth:
    """Test that server requires authentication on all routes except /health."""

    def test_health_allowed_without_token(self, client: Any) -> None:
        """Health check must work without auth token for Docker healthcheck."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "ok"

    def test_health_allowed_with_valid_token(self, client: Any) -> None:
        """Health check also works with a valid token."""
        resp = client.get("/health", headers={"Authorization": "Bearer test-token-123"})
        assert resp.status_code == 200

    def test_evaluate_requires_token(self, client: Any) -> None:
        """POST /evaluate returns 401 without token."""
        resp = client.post(
            "/evaluate",
            data=json.dumps({"expr": "1+1"}),
            content_type="application/json",
        )
        assert resp.status_code == 401
        data = json.loads(resp.data)
        assert "Unauthorized" in data.get("error", "")

    def test_evaluate_accepted_with_valid_token(self, client: Any) -> None:
        """POST /evaluate succeeds with valid token."""
        resp = client.post(
            "/evaluate",
            data=json.dumps({"expr": "1+1"}),
            content_type="application/json",
            headers={"Authorization": "Bearer test-token-123"},
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "ok"

    def test_evaluate_rejects_wrong_token(self, client: Any) -> None:
        """POST /evaluate returns 401 with wrong token."""
        resp = client.post(
            "/evaluate",
            data=json.dumps({"expr": "1+1"}),
            content_type="application/json",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401

    def test_evaluate_rejects_missing_bearer_prefix(self, client: Any) -> None:
        """POST /evaluate returns 401 if Authorization header lacks Bearer prefix."""
        resp = client.post(
            "/evaluate",
            data=json.dumps({"expr": "1+1"}),
            content_type="application/json",
            headers={"Authorization": "test-token-123"},
        )
        assert resp.status_code == 401

    def test_evaluate_with_init_requires_token(self, client: Any) -> None:
        """POST /evaluate-with-init returns 401 without token."""
        resp = client.post(
            "/evaluate-with-init",
            data=json.dumps({"expr": "1+1"}),
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_evaluate_with_init_accepted_with_valid_token(self, client: Any) -> None:
        """POST /evaluate-with-init succeeds with valid token."""
        resp = client.post(
            "/evaluate-with-init",
            data=json.dumps({"expr": "1+1"}),
            content_type="application/json",
            headers={"Authorization": "Bearer test-token-123"},
        )
        assert resp.status_code == 200

    def test_cleanup_requires_token(self, client: Any) -> None:
        """POST /cleanup returns 401 without token."""
        resp = client.post(
            "/cleanup",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_restart_requires_token(self, client: Any) -> None:
        """POST /restart returns 401 without token."""
        resp = client.post(
            "/restart",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_check_state_requires_token(self, client: Any) -> None:
        """GET /check-state returns 401 without token."""
        resp = client.get("/check-state")
        assert resp.status_code == 401


class TestTokenGeneration:
    """Test auto-generation of token when ELEGUA_ORACLE_TOKEN is not set."""

    def test_ephemeral_token_generated(self) -> None:
        """When env var is not set, a token is generated."""
        os.environ.pop("ELEGUA_ORACLE_TOKEN", None)

        # Force clean reload
        for mod_name in list(sys.modules.keys()):
            if "elegua.wolfram.server" in mod_name:
                del sys.modules[mod_name]

        import elegua.wolfram.server  # type: ignore[import-untyped]

        token = elegua.wolfram.server.get_oracle_token()
        assert token is not None
        assert len(token) >= 32  # secrets.token_urlsafe(32) produces ~43 chars

    def test_get_oracle_token_returns_configured_token(self) -> None:
        """get_oracle_token() returns the token from env var."""
        os.environ["ELEGUA_ORACLE_TOKEN"] = "configured-token"

        for mod_name in list(sys.modules.keys()):
            if "elegua.wolfram.server" in mod_name:
                del sys.modules[mod_name]

        import elegua.wolfram.server  # type: ignore[import-untyped]

        token = elegua.wolfram.server.get_oracle_token()
        assert token == "configured-token"
