"""Tests for WolframOracleAdapter and xAct expression builder."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from elegua.task import EleguaTask, TaskStatus
from elegua.wolfram import WolframOracleAdapter
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

    def health(self) -> bool:
        self.calls.append(("health",))
        return self.healthy

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
        return True

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
    adapter = WolframOracleAdapter(oracle=oracle)
    adapter.initialize()
    assert ("health",) in oracle.calls


def test_initialize_fails_when_unhealthy():
    oracle = FakeOracle()
    oracle.healthy = False
    adapter = WolframOracleAdapter(oracle=oracle)
    with pytest.raises(RuntimeError, match="unavailable"):
        adapter.initialize()


def test_teardown_calls_cleanup():
    oracle = FakeOracle()
    adapter = WolframOracleAdapter(oracle=oracle)
    adapter.initialize()
    adapter.teardown()
    assert ("cleanup",) in oracle.calls


def test_context_manager_lifecycle():
    oracle = FakeOracle()
    adapter = WolframOracleAdapter(oracle=oracle)
    with adapter:
        pass
    assert ("health",) in oracle.calls
    assert ("cleanup",) in oracle.calls


# --- Execute: result mapping ---


def test_execute_returns_validation_token():
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="ok", result="T[-a,-b]", type="Expr")
    adapter = WolframOracleAdapter(oracle=oracle)
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
    adapter = WolframOracleAdapter(oracle=oracle)
    with adapter:
        task = EleguaTask(action="Evaluate", payload={"expression": "bad"})
        token = adapter.execute(task)
    assert token.status == TaskStatus.EXECUTION_ERROR
    assert token.metadata.get("error") == "kernel crash"


def test_execute_maps_timeout_status():
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="timeout")
    adapter = WolframOracleAdapter(oracle=oracle)
    with adapter:
        task = EleguaTask(action="Evaluate", payload={"expression": "slow"})
        token = adapter.execute(task)
    assert token.status == TaskStatus.TIMEOUT


def test_default_builder_uses_expression_field():
    """Default expr_builder sends payload['expression'] as-is."""
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="ok", result="0")
    adapter = WolframOracleAdapter(oracle=oracle)
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
    adapter = WolframOracleAdapter(oracle=oracle, expr_builder=build_xact_expr)
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
    adapter = WolframOracleAdapter(oracle=oracle)
    with adapter:
        task = EleguaTask(action="Evaluate", payload={"expression": "1+1"})
        adapter.execute(task)
    assert task.status == TaskStatus.PENDING
    assert task.result is None


# --- Assert special handling ---


def test_assert_true_returns_ok():
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="ok", result="True", type="Bool")
    adapter = WolframOracleAdapter(oracle=oracle, expr_builder=build_xact_expr)
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
    adapter = WolframOracleAdapter(oracle=oracle, expr_builder=build_xact_expr)
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
    adapter = WolframOracleAdapter(oracle=oracle)
    with adapter:
        task = EleguaTask(action="Evaluate", payload={"expression": "T[-a,-b]"})
        token = adapter.execute(task)
    assert token.result is not None
    assert token.result["properties"] == {"rank": 2, "type": "Tensor"}


def test_execute_includes_timing():
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="ok", result="0", timing_ms=42)
    adapter = WolframOracleAdapter(oracle=oracle)
    with adapter:
        task = EleguaTask(action="Evaluate", payload={"expression": "0"})
        token = adapter.execute(task)
    assert token.metadata.get("execution_time_ms") == 42


# --- Oracle connection error ---


def test_execute_handles_oracle_connection_error():
    """Oracle returning error dict (connection failure) maps to EXECUTION_ERROR."""
    oracle = FakeOracle()
    oracle.next_result = FakeResult(status="error", error="Connection refused")
    adapter = WolframOracleAdapter(oracle=oracle)
    with adapter:
        task = EleguaTask(action="Evaluate", payload={"expression": "1+1"})
        token = adapter.execute(task)
    assert token.status == TaskStatus.EXECUTION_ERROR
    assert "Connection refused" in (token.metadata.get("error") or "")
