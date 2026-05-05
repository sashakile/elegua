"""Red-phase tests for vector/array elementwise comparison.

All tests in this file MUST FAIL until elegua.numeric.array is implemented.
See: elegua-ojx, elegua-d5m.
"""

from __future__ import annotations

import pytest

pytest.importorskip(
    "elegua.numeric.array",
    reason="elegua.numeric not yet implemented (elegua-d5m)",
)

from elegua.models import ValidationToken
from elegua.numeric.array import ArrayComparisonResult, make_array_comparator
from elegua.numeric.tolerance import AbsoluteTolerance, MixedTolerance
from elegua.task import TaskStatus


def _array_token(values: list[float]) -> ValidationToken:
    return ValidationToken(
        adapter_id="test",
        status=TaskStatus.OK,
        result={"values": values},
    )


# --- Passing comparisons ---


def test_identical_arrays_ok():
    compare = make_array_comparator(tolerance=AbsoluteTolerance(atol=1e-6))
    a = _array_token([1.0, 2.0, 3.0])
    b = _array_token([1.0, 2.0, 3.0])
    assert compare(a, b) == TaskStatus.OK


def test_arrays_within_tolerance_ok():
    compare = make_array_comparator(tolerance=AbsoluteTolerance(atol=1e-4))
    a = _array_token([1.0, 2.0, 3.0])
    b = _array_token([1.00005, 2.00005, 3.00005])
    assert compare(a, b) == TaskStatus.OK


def test_single_element_array_ok():
    compare = make_array_comparator(tolerance=AbsoluteTolerance(atol=1e-6))
    assert compare(_array_token([42.0]), _array_token([42.0])) == TaskStatus.OK


# --- Failing comparisons ---


def test_one_element_exceeds_tolerance_fails():
    compare = make_array_comparator(tolerance=AbsoluteTolerance(atol=1e-6))
    a = _array_token([1.0, 2.0, 3.0])
    b = _array_token([1.0, 2.0, 4.0])  # index 2 disagrees
    assert compare(a, b) == TaskStatus.MATH_MISMATCH


def test_all_elements_exceed_tolerance_fails():
    compare = make_array_comparator(tolerance=AbsoluteTolerance(atol=1e-6))
    a = _array_token([1.0, 2.0])
    b = _array_token([2.0, 3.0])
    assert compare(a, b) == TaskStatus.MATH_MISMATCH


# --- Shape mismatch ---


def test_shape_mismatch_is_mismatch():
    compare = make_array_comparator(tolerance=AbsoluteTolerance(atol=1e-6))
    a = _array_token([1.0, 2.0, 3.0])
    b = _array_token([1.0, 2.0])
    assert compare(a, b) == TaskStatus.MATH_MISMATCH


# --- Missing values field ---


def test_missing_values_field_is_mismatch():
    compare = make_array_comparator(tolerance=AbsoluteTolerance(atol=1e-6))
    no_values = ValidationToken(adapter_id="test", status=TaskStatus.OK, result={})
    assert compare(no_values, _array_token([1.0])) == TaskStatus.MATH_MISMATCH


# --- ArrayComparisonResult diagnostics ---


def test_result_includes_max_disagreement():
    compare = make_array_comparator(tolerance=AbsoluteTolerance(atol=1e-6), return_diagnostics=True)
    a = _array_token([1.0, 2.0, 3.0])
    b = _array_token([1.0, 2.5, 3.1])
    result: ArrayComparisonResult = compare(a, b)
    assert result.max_disagreement == pytest.approx(0.5)


def test_result_includes_argmax_location():
    compare = make_array_comparator(tolerance=AbsoluteTolerance(atol=1e-6), return_diagnostics=True)
    a = _array_token([1.0, 2.0, 3.0])
    b = _array_token([1.0, 2.5, 3.1])
    result: ArrayComparisonResult = compare(a, b)
    assert result.argmax_location == 1  # index 1 has largest disagreement (0.5)


def test_result_includes_failing_count():
    compare = make_array_comparator(tolerance=AbsoluteTolerance(atol=0.2), return_diagnostics=True)
    a = _array_token([1.0, 2.0, 3.0, 4.0])
    b = _array_token([1.0, 2.5, 3.5, 4.0])  # indices 1 and 2 fail (delta > 0.2)
    result: ArrayComparisonResult = compare(a, b)
    assert result.failing_count == 2


def test_result_full_arrays_not_in_verdict():
    compare = make_array_comparator(tolerance=AbsoluteTolerance(atol=1e-6), return_diagnostics=True)
    a = _array_token(list(range(1000)))
    b = _array_token([float(i) + 0.1 for i in range(1000)])
    result: ArrayComparisonResult = compare(a, b)
    assert not hasattr(result, "expected_array")
    assert not hasattr(result, "actual_array")


def test_result_top_k_disagreements_default_five():
    compare = make_array_comparator(tolerance=AbsoluteTolerance(atol=1e-6), return_diagnostics=True)
    values_a = [0.0] * 10
    values_b = [float(i) for i in range(10)]  # all disagree
    a, b = _array_token(values_a), _array_token(values_b)
    result: ArrayComparisonResult = compare(a, b)
    assert len(result.top_k_disagreements) <= 5


def test_result_top_k_entries_have_required_fields():
    compare = make_array_comparator(tolerance=AbsoluteTolerance(atol=1e-6), return_diagnostics=True)
    a = _array_token([0.0, 0.0, 0.0])
    b = _array_token([1.0, 2.0, 3.0])
    result: ArrayComparisonResult = compare(a, b)
    assert len(result.top_k_disagreements) == 3
    for entry in result.top_k_disagreements:
        assert hasattr(entry, "index") or isinstance(entry, tuple)
        # Each entry: (index, expected, actual, delta)
        idx, _expected, _actual, delta = (
            entry
            if isinstance(entry, tuple)
            else (entry.index, entry.expected, entry.actual, entry.delta)
        )
        assert isinstance(idx, int)
        assert isinstance(delta, float)


def test_mixed_tolerance_array_ok():
    compare = make_array_comparator(tolerance=MixedTolerance(atol=1e-8, rtol=1e-4))
    a = _array_token([100.0, 200.0])
    b = _array_token([100.005, 200.01])
    assert compare(a, b) == TaskStatus.OK


def test_configurable_k_limits_top_k():
    values_a = [0.0] * 20
    values_b = [float(i) for i in range(20)]
    result: ArrayComparisonResult = make_array_comparator(
        tolerance=AbsoluteTolerance(atol=1e-6), k=3, return_diagnostics=True
    )(_array_token(values_a), _array_token(values_b))
    assert len(result.top_k_disagreements) <= 3
