"""Unit tests for OracleClient HTTP client."""

import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from elegua.oracle import OracleClient


def _mock_response(data):
    """Create a mock urlopen response (context-manager compatible)."""
    mock_resp = MagicMock()
    if isinstance(data, dict):
        mock_resp.read.return_value = json.dumps(data).encode()
    else:
        mock_resp.read.return_value = data
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestHealth:
    def test_healthy(self):
        client = OracleClient("http://fake:1234")
        with patch("urllib.request.urlopen", return_value=_mock_response({"status": "ok"})):
            assert client.health() is True

    def test_unhealthy_status(self):
        client = OracleClient("http://fake:1234")
        with patch("urllib.request.urlopen", return_value=_mock_response({"status": "error"})):
            assert client.health() is False

    def test_connection_refused(self):
        client = OracleClient("http://fake:1234")
        with patch("urllib.request.urlopen", side_effect=ConnectionRefusedError("refused")):
            assert client.health() is False

    def test_url_error(self):
        client = OracleClient("http://fake:1234")
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("no host")):
            assert client.health() is False

    def test_malformed_json(self):
        client = OracleClient("http://fake:1234")
        with patch("urllib.request.urlopen", return_value=_mock_response(b"not json")):
            assert client.health() is False


class TestHealthOrRaise:
    def test_healthy_no_exception(self):
        client = OracleClient("http://fake:1234")
        with patch("urllib.request.urlopen", return_value=_mock_response({"status": "ok"})):
            client.health_or_raise()  # should not raise

    def test_connection_refused_chains_cause(self):
        client = OracleClient("http://fake:1234")
        original = ConnectionRefusedError("refused")
        with patch("urllib.request.urlopen", side_effect=original):
            with pytest.raises(RuntimeError, match="Oracle unavailable") as exc_info:
                client.health_or_raise()
            assert exc_info.value.__cause__ is original

    def test_unhealthy_status(self):
        client = OracleClient("http://fake:1234")
        with (
            patch("urllib.request.urlopen", return_value=_mock_response({"status": "degraded"})),
            pytest.raises(RuntimeError, match=r"unhealthy.*degraded"),
        ):
            client.health_or_raise()


class TestEvaluateWithXact:
    def test_success(self):
        client = OracleClient("http://fake:1234")
        resp = {"status": "ok", "result": "42"}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = client.evaluate_with_xact("1+1")
        assert result == resp

    def test_connection_error_returns_error_dict(self):
        client = OracleClient("http://fake:1234")
        with patch("urllib.request.urlopen", side_effect=ConnectionRefusedError("refused")):
            result = client.evaluate_with_xact("1+1")
        assert result["status"] == "error"
        assert "refused" in result["error"]

    def test_json_decode_error_returns_error_dict(self):
        client = OracleClient("http://fake:1234")
        with patch("urllib.request.urlopen", return_value=_mock_response(b"not json")):
            result = client.evaluate_with_xact("1+1")
        assert result["status"] == "error"

    def test_context_id_in_request(self):
        client = OracleClient("http://fake:1234")
        resp = {"status": "ok", "result": "42"}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)) as mock_open:
            client.evaluate_with_xact("1+1", context_id="ctx-123")
            call_args = mock_open.call_args
            req = call_args[0][0]
            body = json.loads(req.data)
            assert body["context_id"] == "ctx-123"


class TestCleanup:
    def test_success(self):
        client = OracleClient("http://fake:1234")
        with patch("urllib.request.urlopen", return_value=_mock_response({"status": "ok"})):
            assert client.cleanup() is True

    def test_failure(self):
        client = OracleClient("http://fake:1234")
        with patch("urllib.request.urlopen", side_effect=ConnectionRefusedError()):
            assert client.cleanup() is False


class TestCheckCleanState:
    def test_clean(self):
        client = OracleClient("http://fake:1234")
        resp = _mock_response({"clean": True, "leaked": []})
        with patch("urllib.request.urlopen", return_value=resp):
            clean, leaked = client.check_clean_state()
        assert clean is True
        assert leaked == []

    def test_dirty(self):
        client = OracleClient("http://fake:1234")
        with patch(
            "urllib.request.urlopen",
            return_value=_mock_response({"clean": False, "leaked": ["$foo"]}),
        ):
            clean, leaked = client.check_clean_state()
        assert clean is False
        assert leaked == ["$foo"]

    def test_error_returns_defaults(self):
        client = OracleClient("http://fake:1234")
        with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
            clean, leaked = client.check_clean_state()
        assert clean is False
        assert leaked == []


class TestBaseUrl:
    def test_trailing_slash_stripped(self):
        client = OracleClient("http://fake:1234/")
        assert client.base_url == "http://fake:1234"
