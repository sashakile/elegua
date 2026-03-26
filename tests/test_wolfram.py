"""Tests for OracleAdapter and xAct expression builder."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from elegua.models import ValidationToken
from elegua.task import EleguaTask, TaskStatus
from elegua.wolfram.adapter import OracleAdapter
from tests.xact_builder import build_xact_expr

# --- Fake oracle for unit tests ---


@dataclass
class FakeResult:
    status: str = "ok"
    result: str = ""
    type: str = "Expr"
    properties: dict[str, Any] = field(default_factory=dict)
    timing_ms: int | None = None
    error: str | None = None


class FakeOracle:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.healthy: bool = True
        self.clean: bool = True
        self.leaked: list[str] = []
        self.next_result: FakeResult = FakeResult()
        self._health_error: Exception | None = None
        self._cleanup_ok: bool = True

    def health(self) -> bool:
        self.calls.append(("health",))
        return self.healthy

    def health_or_raise(self) -> None:
        self.calls.append(("health_or_raise",))
        if self._health_error is not None:
            raise RuntimeError(f"Oracle unavailable: {self._health_error}") from self._health_error
        if not self.healthy:
            raise RuntimeError("Oracle unhealthy (status='not-ok')")

    def evaluate_with_xact(
        self,
        expr: str,
        timeout: int = 60,
        context_id: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append(("evaluate", expr))
        r = self.next_result
        result: dict[str, Any] = {
            "status": r.status,
            "result": r.result,
            "type": r.type,
            "properties": r.properties,
        }
        if r.timing_ms is not None:
            result["timing_ms"] = r.timing_ms
        if r.error is not None:
            result["error"] = r.error
        return result

    def cleanup(self) -> bool:
        self.calls.append(("cleanup",))
        return self._cleanup_ok

    def check_clean_state(self) -> tuple[bool, list[str]]:
        self.calls.append(("check_clean_state",))
        return self.clean, self.leaked


# --- build_xact_expr: xAct action → Wolfram expression ---


@pytest.mark.parametrize(
    "action, args, expected",
    [
        (
            "DefManifold",
            {"name": "M", "dimension": 4, "indices": ["a", "b", "c", "d"]},
            "DefManifold[M, 4, {a, b, c, d}]",
        ),
        (
            "DefMetric",
            {"signdet": -1, "metric": "g[-a,-b]", "covd": "CD"},
            "DefMetric[-1, g[-a,-b], CD]",
        ),
        (
            "DefTensor",
            {"name": "T", "indices": ["-a", "-b"], "manifold": "M"},
            "DefTensor[T[-a,-b], M]",
        ),
        (
            "DefTensor",
            {
                "name": "S",
                "indices": ["-a", "-b"],
                "manifold": "M",
                "symmetry": "Symmetric[{-a,-b}]",
            },
            "DefTensor[S[-a,-b], M, Symmetric[{-a,-b}]]",
        ),
        (
            "Evaluate",
            {"expression": "T[-a,-b] + T[-b,-a]"},
            "T[-a,-b] + T[-b,-a]",
        ),
        (
            "ToCanonical",
            {"expression": "T[-a,-b] - T[-b,-a]"},
            "ToCanonical[T[-a,-b] - T[-b,-a]]",
        ),
        (
            "Simplify",
            {"expression": "T[-a,-b]"},
            "Simplify[T[-a,-b]]",
        ),
        (
            "Contract",
            {"expression": "g[a,b] T[-a,-b]"},
            "ContractMetric[g[a,b] T[-a,-b]]",
        ),
        (
            "Assert",
            {"condition": "TensorQ[T] === True"},
            "TensorQ[T] === True",
        ),
        (
            "CommuteCovDs",
            {
                "expression": "CD[-a][CD[-b][T[-c]]]",
                "covd": "CD",
                "indices": ["-a", "-b"],
            },
            "CommuteCovDs[CD[-a][CD[-b][T[-c]]], CD, {-a, -b}]",
        ),
        (
            "IntegrateByParts",
            {"expression": "CD[-a][V[a]] T[-b]", "covd": "CD"},
            "IBP[CD[-a][V[a]] T[-b], CD]",
        ),
        (
            "VarD",
            {"expression": "L", "field": "g", "covd": "CD"},
            "VarD[g, CD][L]",
        ),
    ],
)
def test_build_xact_expr(action: str, args: dict[str, Any], expected: str):
    assert build_xact_expr(action, args) == expected


def test_build_xact_expr_unknown_action():
    with pytest.raises(ValueError, match="Unknown xAct action"):
        build_xact_expr("NoSuchAction", {})


def test_build_xact_expr_missing_arg():
    with pytest.raises(KeyError):
        build_xact_expr("DefManifold", {"name": "M"})


# --- Adapter lifecycle ---


def test_initialize_checks_health():
    oracle = FakeOracle()
    adapter = OracleAdapter(oracle=oracle)
    adapter.initialize()
    assert ("health_or_raise",) in oracle.calls


def test_initialize_fails_when_unhealthy():
    oracle = FakeOracle()
    oracle.healthy = False
    adapter = OracleAdapter(oracle=oracle)
    with pytest.raises(RuntimeError, match=r"unhealthy|unavailable"):
        adapter.initialize()


def test_teardown_calls_cleanup():
    oracle = FakeOracle()
    adapter = OracleAdapter(oracle=oracle)
    adapter.initialize()
    adapter.teardown()
    assert ("cleanup",) in oracle.calls


def test_context_manager_lifecycle():
    oracle = FakeOracle()
    adapter = OracleAdapter(oracle=oracle)
    with adapter:
        pass
    assert ("health_or_raise",) in oracle.calls
    assert ("cleanup",) in oracle.calls


# --- Execute: result mapping ---


def test_execute_returns_validation_token():
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="ok", result="T[-a,-b]", type="Expr")
    adapter = OracleAdapter(oracle=oracle)
    with adapter:
        task = EleguaTask(action="Evaluate", payload={"expression": "T[-a,-b]"})
        token = adapter.execute(task)
    assert token.adapter_id == "wolfram-oracle"
    assert token.status == TaskStatus.OK
    assert token.result is not None
    assert token.result["repr"] == "T[-a,-b]"
    assert token.result["type"] == "Expr"


def test_execute_maps_error_status():
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="error", error="kernel crash")
    adapter = OracleAdapter(oracle=oracle)
    with adapter:
        task = EleguaTask(action="Evaluate", payload={"expression": "bad"})
        token = adapter.execute(task)
    assert token.status == TaskStatus.EXECUTION_ERROR
    assert token.metadata.get("error") == "kernel crash"


def test_execute_maps_timeout_status():
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="timeout")
    adapter = OracleAdapter(oracle=oracle)
    with adapter:
        task = EleguaTask(action="Evaluate", payload={"expression": "slow"})
        token = adapter.execute(task)
    assert token.status == TaskStatus.TIMEOUT


def test_default_builder_uses_expression_field():
    """Default expr_builder sends payload['expression'] as-is."""
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="ok", result="0")
    adapter = OracleAdapter(oracle=oracle)
    with adapter:
        task = EleguaTask(
            action="Evaluate",
            payload={"expression": "1 + 1"},
        )
        adapter.execute(task)
    eval_calls = [c for c in oracle.calls if c[0] == "evaluate"]
    assert eval_calls[0][1] == "1 + 1"


def test_custom_expr_builder():
    """Custom expr_builder translates actions to Wolfram expressions."""
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="ok", result="0")
    adapter = OracleAdapter(oracle=oracle, expr_builder=build_xact_expr)
    with adapter:
        task = EleguaTask(
            action="ToCanonical",
            payload={"expression": "T[-a,-b] - T[-b,-a]"},
        )
        adapter.execute(task)
    eval_calls = [c for c in oracle.calls if c[0] == "evaluate"]
    assert eval_calls[0][1] == "ToCanonical[T[-a,-b] - T[-b,-a]]"


def test_execute_does_not_mutate_task():
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="ok", result="ok")
    adapter = OracleAdapter(oracle=oracle)
    with adapter:
        task = EleguaTask(action="Evaluate", payload={"expression": "1+1"})
        adapter.execute(task)
    assert task.status == TaskStatus.PENDING
    assert task.result is None


# --- Assert special handling ---


def test_assert_true_returns_ok():
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="ok", result="True", type="Bool")
    adapter = OracleAdapter(oracle=oracle, expr_builder=build_xact_expr)
    with adapter:
        task = EleguaTask(
            action="Assert",
            payload={"condition": "TensorQ[T] === True"},
        )
        token = adapter.execute(task)
    assert token.status == TaskStatus.OK


def test_assert_false_returns_error():
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="ok", result="False", type="Bool")
    adapter = OracleAdapter(oracle=oracle, expr_builder=build_xact_expr)
    with adapter:
        task = EleguaTask(
            action="Assert",
            payload={"condition": "TensorQ[X]", "message": "X is not a tensor"},
        )
        token = adapter.execute(task)
    assert token.status == TaskStatus.EXECUTION_ERROR
    assert "X is not a tensor" in (token.metadata.get("error") or "")


# --- Properties and metadata ---


def test_execute_includes_properties():
    oracle = FakeOracle()
    oracle.next_result = FakeResult(
        status="ok",
        result="T[-a,-b]",
        properties={"rank": 2, "type": "Tensor"},
    )
    adapter = OracleAdapter(oracle=oracle)
    with adapter:
        task = EleguaTask(action="Evaluate", payload={"expression": "T[-a,-b]"})
        token = adapter.execute(task)
    assert token.result is not None
    assert token.result["properties"] == {"rank": 2, "type": "Tensor"}


def test_execute_includes_timing():
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="ok", result="0", timing_ms=42)
    adapter = OracleAdapter(oracle=oracle)
    with adapter:
        task = EleguaTask(action="Evaluate", payload={"expression": "0"})
        token = adapter.execute(task)
    assert token.metadata.get("execution_time_ms") == 42


# --- Oracle connection error ---


def test_execute_handles_oracle_connection_error():
    """Oracle returning error dict (connection failure) maps to EXECUTION_ERROR."""
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="error", error="Connection refused")
    adapter = OracleAdapter(oracle=oracle)
    with adapter:
        task = EleguaTask(action="Evaluate", payload={"expression": "1+1"})
        token = adapter.execute(task)
    assert token.status == TaskStatus.EXECUTION_ERROR
    assert "Connection refused" in (token.metadata.get("error") or "")


# --- health_or_raise: root cause preservation ---


def test_initialize_unhealthy_includes_cause():
    """When health check fails due to network error, RuntimeError chains the original."""
    oracle = FakeOracle()
    oracle._health_error = ConnectionRefusedError("Connection refused")
    adapter = OracleAdapter(oracle=oracle)
    with pytest.raises(RuntimeError, match="unavailable") as exc_info:
        adapter.initialize()
    assert exc_info.value.__cause__ is oracle._health_error


def test_initialize_calls_health_or_raise():
    """initialize() should call health_or_raise(), not just health()."""
    oracle = FakeOracle()
    adapter = OracleAdapter(oracle=oracle)
    adapter.initialize()
    assert ("health_or_raise",) in oracle.calls


def test_initialize_unhealthy_no_network_error():
    """When health_or_raise reports unhealthy (no network error), RuntimeError is raised."""
    oracle = FakeOracle()
    oracle.healthy = False
    adapter = OracleAdapter(oracle=oracle)
    with pytest.raises(RuntimeError, match=r"unhealthy|unavailable"):
        adapter.initialize()


# --- OracleClient: JSONDecodeError handling (M6) ---


def test_evaluate_with_xact_handles_json_decode_error():
    """Malformed JSON response should be caught as a decode error."""
    from unittest.mock import MagicMock, patch

    from elegua.oracle import OracleClient

    client = OracleClient("http://fake:1234")
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"not json at all"
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = client.evaluate_with_xact("1+1")

    assert result["status"] == "error"
    assert "error" in result


# --- Teardown warns on cleanup failure (L5) ---


def test_teardown_warns_on_cleanup_failure():
    oracle = FakeOracle()
    oracle._cleanup_ok = False
    adapter = OracleAdapter(oracle=oracle)
    adapter.initialize()
    with pytest.warns(RuntimeWarning, match="cleanup failed"):
        adapter.teardown()


# --- execute without initialize (elegua-1u1) ---


def test_execute_without_initialize_raises():
    """execute() without initialize() must raise, not silently use Global context."""
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="ok", result="1")
    adapter = OracleAdapter(oracle=oracle)
    # Do NOT call adapter.initialize()
    task = EleguaTask(action="Evaluate", payload={"expression": "1+1"})
    with pytest.raises(RuntimeError, match="initialize"):
        adapter.execute(task)


# --- Configurable adapter_id (elegua-85f) ---


def test_adapter_id_defaults_to_wolfram_oracle():
    adapter = OracleAdapter(oracle=FakeOracle())
    assert adapter.adapter_id == "wolfram-oracle"


def test_adapter_id_configurable():
    adapter = OracleAdapter(oracle=FakeOracle(), adapter_id="julia")
    assert adapter.adapter_id == "julia"


def test_custom_adapter_id_in_tokens():
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="ok", result="42")
    adapter = OracleAdapter(oracle=oracle, adapter_id="julia")
    adapter.initialize()
    task = EleguaTask(action="Evaluate", payload={"expression": "21*2"})
    token = adapter.execute(task)
    assert token.adapter_id == "julia"
    adapter.teardown()


def test_wolfram_oracle_adapter_emits_deprecation_warning():
    from elegua.wolfram.adapter import WolframOracleAdapter

    oracle = FakeOracle()
    with pytest.warns(DeprecationWarning, match="WolframOracleAdapter is deprecated"):
        WolframOracleAdapter(oracle=oracle)


# --- Injectable result_mapper ---


def test_custom_result_mapper_called():
    """When result_mapper is provided, execute() delegates to it."""
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="ok", result="42")
    calls: list[tuple[str, dict, dict]] = []

    def mapper(action: str, payload: dict[str, Any], data: dict[str, Any]) -> ValidationToken:
        calls.append((action, payload, data))
        return ValidationToken(adapter_id="custom", status=TaskStatus.OK, result={"custom": True})

    adapter = OracleAdapter(oracle=oracle, result_mapper=mapper)
    with adapter:
        task = EleguaTask(action="Evaluate", payload={"expression": "21*2"})
        token = adapter.execute(task)

    assert len(calls) == 1
    assert calls[0][0] == "Evaluate"
    assert token.result == {"custom": True}


def test_default_result_mapper_preserved():
    """When result_mapper is None, default _map_result behavior works."""
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="ok", result="T[-a,-b]", type="Expr")
    adapter = OracleAdapter(oracle=oracle, result_mapper=None)
    with adapter:
        task = EleguaTask(action="Evaluate", payload={"expression": "T[-a,-b]"})
        token = adapter.execute(task)
    assert token.status == TaskStatus.OK
    assert token.result is not None
    assert token.result["repr"] == "T[-a,-b]"
