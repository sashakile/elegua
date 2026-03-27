"""Tests for SympyAdapter — action dispatch, timeout, and error handling."""

from __future__ import annotations

from elegua.adapter import Adapter
from elegua.sympy.adapter import SympyAdapter
from elegua.task import EleguaTask, TaskStatus

# --- Adapter identity ---


def test_is_adapter_subclass():
    adapter = SympyAdapter()
    assert isinstance(adapter, Adapter)


def test_adapter_id():
    adapter = SympyAdapter()
    assert adapter.adapter_id == "sympy"


# --- Action dispatch ---


def test_integrate_sin():
    adapter = SympyAdapter()
    task = EleguaTask(
        action="Integrate",
        payload={"expression": "Sin[x]", "variable": "x"},
    )
    token = adapter.execute(task)
    assert token.status == TaskStatus.OK
    assert token.result is not None
    assert "cos" in token.result["repr"].lower()


def test_differentiate():
    adapter = SympyAdapter()
    task = EleguaTask(
        action="Differentiate",
        payload={"expression": "x**3/3", "variable": "x"},
    )
    token = adapter.execute(task)
    assert token.status == TaskStatus.OK
    assert token.result is not None
    assert "x**2" in token.result["repr"]


def test_simplify():
    adapter = SympyAdapter()
    task = EleguaTask(
        action="Simplify",
        payload={"expression": "x**2 + 2*x + 1"},
    )
    token = adapter.execute(task)
    assert token.status == TaskStatus.OK
    assert token.result is not None


def test_solve():
    adapter = SympyAdapter()
    task = EleguaTask(
        action="Solve",
        payload={"expression": "x**2 - 4", "variable": "x"},
    )
    token = adapter.execute(task)
    assert token.status == TaskStatus.OK
    assert token.result is not None


def test_series():
    adapter = SympyAdapter()
    task = EleguaTask(
        action="Series",
        payload={"expression": "Sin[x]", "variable": "x"},
    )
    token = adapter.execute(task)
    assert token.status == TaskStatus.OK


def test_limit():
    adapter = SympyAdapter()
    task = EleguaTask(
        action="Limit",
        payload={"expression": "Sin[x]/x", "variable": "x", "point": "0"},
    )
    token = adapter.execute(task)
    assert token.status == TaskStatus.OK
    assert token.result is not None
    assert token.result["repr"] == "1"


# --- Error cases ---


def test_unknown_action():
    adapter = SympyAdapter()
    task = EleguaTask(action="UnknownAction", payload={"expression": "x"})
    token = adapter.execute(task)
    assert token.status == TaskStatus.EXECUTION_ERROR
    assert "UnknownAction" in (token.metadata.get("error") or "")


def test_missing_variable():
    adapter = SympyAdapter()
    task = EleguaTask(
        action="Integrate",
        payload={"expression": "x**2"},
    )
    token = adapter.execute(task)
    assert token.status == TaskStatus.EXECUTION_ERROR


# --- Result format ---


def test_result_has_repr_type_properties():
    adapter = SympyAdapter()
    task = EleguaTask(
        action="Simplify",
        payload={"expression": "x + 1"},
    )
    token = adapter.execute(task)
    assert token.result is not None
    assert "repr" in token.result
    assert "type" in token.result
    assert "properties" in token.result
    assert token.result["properties"] == {}


# --- Unevaluated integral detection ---


def test_unevaluated_integral_flagged():
    """When SymPy cannot solve an integral, metadata['unevaluated'] = True."""
    adapter = SympyAdapter()
    task = EleguaTask(
        action="Integrate",
        payload={"expression": "x**x", "variable": "x"},
    )
    token = adapter.execute(task)
    assert token.status == TaskStatus.OK
    assert token.metadata.get("unevaluated") is True
    assert "Integral" in token.result["repr"]


# --- Timeout ---


def test_timeout_returns_timeout_status():
    """Timeout on long-running operation returns TIMEOUT within bound."""
    import time

    adapter = SympyAdapter(timeout=1.0)
    task = EleguaTask(
        action="Integrate",
        payload={
            "expression": "exp(sin(x**3) + cos(x**5)) * tan(x**7)",
            "variable": "x",
        },
    )
    start = time.monotonic()
    token = adapter.execute(task)
    elapsed = time.monotonic() - start
    assert token.status == TaskStatus.TIMEOUT
    assert elapsed < 4.0, f"Timeout took too long: {elapsed:.1f}s"
