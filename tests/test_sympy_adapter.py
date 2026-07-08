"""Tests for SympyAdapter — action dispatch, timeout, and error handling."""

from __future__ import annotations

import pytest

from elegua.adapter import Adapter

pytest.importorskip("sympy")

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


def test_timeout_no_leaked_threads_after_return():
    """After timeout, no daemon threads remain that were spawned by the adapter."""
    import threading
    import time

    # Use a task that would take very long
    adapter = SympyAdapter(timeout=0.5)
    task = EleguaTask(
        action="Integrate",
        payload={
            "expression": "exp(sin(x**3) + cos(x**5)) * tan(x**7)",
            "variable": "x",
        },
    )

    # Count threads before
    names_before = {t.name for t in threading.enumerate()}

    token = adapter.execute(task)
    assert token.status == TaskStatus.TIMEOUT

    # Small delay for cleanup
    time.sleep(1.0)

    names_after = {t.name for t in threading.enumerate()}
    # The daemon thread from the old implementation is named "Thread-N (target)"
    # After the fix, no such thread should remain
    leaked = {n for n in names_after - names_before}
    # Filter out benign system threads
    leaked = {n for n in leaked
              if not any(ignore in n.lower()
                        for ignore in ["pytest", "pydev", "asyncio", "mainthread"])}
    assert len(leaked) == 0, f"Leaked threads after timeout: {leaked}"


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


# --- Numeric sample generation ---


def test_sample_points_happy_path():
    """Constructor sample_points generates numeric_samples in result."""
    adapter = SympyAdapter(
        sample_points=[{"x": 0.5}, {"x": 1.0}, {"x": 2.0}],
    )
    task = EleguaTask(
        action="Integrate",
        payload={"expression": "x**2", "variable": "x"},
    )
    token = adapter.execute(task)
    assert token.status == TaskStatus.OK
    samples = token.result["numeric_samples"]
    assert len(samples) == 3
    for s in samples:
        assert "vars" in s
        assert "value" in s
        assert isinstance(s["value"], float)


def test_sample_points_skips_pole():
    """Points causing domain errors (for example, 1/x at x=0) are skipped."""
    adapter = SympyAdapter(
        sample_points=[{"x": 0.0}, {"x": 1.0}],
    )
    task = EleguaTask(
        action="Simplify",
        payload={"expression": "1/x"},
    )
    token = adapter.execute(task)
    assert token.status == TaskStatus.OK
    samples = token.result["numeric_samples"]
    assert len(samples) == 1
    assert samples[0]["vars"] == {"x": 1.0}
    assert samples[0]["value"] == 1.0


def test_sample_points_includes_nan_inf_as_non_finite():
    """Points producing nan or inf are included with non_finite flag."""
    adapter = SympyAdapter(
        sample_points=[{"x": 0.0}, {"x": 1.0}],
    )
    # log(0) → -inf, log(1) → 0
    task = EleguaTask(
        action="Simplify",
        payload={"expression": "log(x)"},
    )
    token = adapter.execute(task)
    assert token.status == TaskStatus.OK
    samples = token.result["numeric_samples"]
    assert len(samples) == 2
    inf = next(s for s in samples if s["vars"] == {"x": 0.0})
    assert inf.get("non_finite") is True
    fin = next(s for s in samples if s["vars"] == {"x": 1.0})
    assert "non_finite" not in fin or fin["non_finite"] is False
    assert fin["value"] == 0.0


def test_sample_points_complex_flagged_non_finite():
    """Complex results produce nan via numpy and are flagged non_finite."""
    adapter = SympyAdapter(
        sample_points=[{"x": -1.0}, {"x": 1.0}],
    )
    # sqrt(-1) → nan (via numpy), sqrt(1) → 1.0
    task = EleguaTask(
        action="Simplify",
        payload={"expression": "sqrt(x)"},
    )
    token = adapter.execute(task)
    assert token.status == TaskStatus.OK
    samples = token.result["numeric_samples"]
    assert len(samples) == 2
    nf = next(s for s in samples if s["vars"] == {"x": -1.0})
    assert nf.get("non_finite") is True
    fin = next(s for s in samples if s["vars"] == {"x": 1.0})
    assert "non_finite" not in fin or fin["non_finite"] is False
    assert fin["value"] == 1.0


def test_no_sample_points_no_key():
    """Without sample_points configured, result has no numeric_samples key."""
    adapter = SympyAdapter()
    task = EleguaTask(
        action="Simplify",
        payload={"expression": "x + 1"},
    )
    token = adapter.execute(task)
    assert token.status == TaskStatus.OK
    assert "numeric_samples" not in token.result


def test_sample_points_includes_nan_inf():
    """Points producing nan or inf are included with non_finite flag."""
    adapter = SympyAdapter(
        sample_points=[{"x": 0.0}, {"x": 1.0}],
    )
    # log(0) → -inf, log(1) → 0
    task = EleguaTask(
        action="Simplify",
        payload={"expression": "log(x)"},
    )
    token = adapter.execute(task)
    assert token.status == TaskStatus.OK
    samples = token.result["numeric_samples"]
    assert len(samples) == 2
    # x=0.0 should be non-finite
    inf_sample = next(s for s in samples if s["vars"]["x"] == 0.0)
    assert inf_sample.get("non_finite") is True
    assert inf_sample.get("value") is None
    # x=1.0 should be finite
    finite_sample = next(s for s in samples if s["vars"]["x"] == 1.0)
    assert "non_finite" not in finite_sample or finite_sample["non_finite"] is False
    assert isinstance(finite_sample["value"], float)


def test_sample_points_all_nan_returns_samples():
    """When all points produce NaN, samples list is non-empty with non_finite flags."""
    adapter = SympyAdapter(
        sample_points=[{"x": 0.0}, {"x": -1.0}],
    )
    # log(0) → -inf, log(-1) → nan (complex) — complex currently skipped
    # Use a function that returns nan at both points
    task = EleguaTask(
        action="Simplify",
        payload={"expression": "log(abs(x)) / log(x)"},
    )
    token = adapter.execute(task)
    assert token.status == TaskStatus.OK
    samples = token.result["numeric_samples"]
    # At least x=0.0 should produce a non_finite entry
    non_finite = [s for s in samples if s.get("non_finite")]
    assert len(non_finite) >= 1


def test_l4_equivalent_forms():
    """L4 integration test: log(a)+log(b) vs log(a*b) produce same samples."""
    adapter = SympyAdapter(
        sample_points=[{"a": 2.0, "b": 3.0}, {"a": 1.0, "b": 5.0}],
    )
    # Two equivalent expressions
    task_a = EleguaTask(
        action="Simplify",
        payload={"expression": "log(a) + log(b)"},
    )
    task_b = EleguaTask(
        action="Simplify",
        payload={"expression": "log(a*b)"},
    )
    token_a = adapter.execute(task_a)
    token_b = adapter.execute(task_b)

    samples_a = token_a.result["numeric_samples"]
    samples_b = token_b.result["numeric_samples"]
    assert len(samples_a) == 2
    assert len(samples_b) == 2
    for sa, sb in zip(samples_a, samples_b, strict=True):
        assert abs(sa["value"] - sb["value"]) < 1e-10
