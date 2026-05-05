"""Red-phase tests for top-K array disagreement diagnostics in verdicts.

All tests in this file MUST FAIL until elegua.numeric.array is implemented.
See: elegua-q2ch, elegua-jwox.
"""

from __future__ import annotations

from elegua.models import ValidationToken
from elegua.numeric.array import make_array_comparator
from elegua.numeric.tolerance import AbsoluteTolerance
from elegua.task import TaskStatus


def _array_token(values: list[float]) -> ValidationToken:
    return ValidationToken(
        adapter_id="test",
        status=TaskStatus.OK,
        result={"values": values},
    )


# --- top_k_disagreements field present in failing verdicts ---


def test_failing_verdict_has_top_k_disagreements():
    compare = make_array_comparator(tolerance=AbsoluteTolerance(atol=1e-6), return_diagnostics=True)
    a = _array_token([0.0, 0.0, 0.0])
    b = _array_token([1.0, 2.0, 3.0])
    result = compare(a, b)
    assert hasattr(result, "top_k_disagreements")


def test_top_k_disagreements_has_at_most_k_entries_default():
    compare = make_array_comparator(tolerance=AbsoluteTolerance(atol=1e-6), return_diagnostics=True)
    a = _array_token([0.0] * 20)
    b = _array_token([float(i) for i in range(20)])
    result = compare(a, b)
    # Default K is 5
    assert len(result.top_k_disagreements) <= 5


def test_top_k_disagreements_configurable():
    compare = make_array_comparator(
        tolerance=AbsoluteTolerance(atol=1e-6), k=10, return_diagnostics=True
    )
    a = _array_token([0.0] * 50)
    b = _array_token([float(i) for i in range(50)])
    result = compare(a, b)
    assert len(result.top_k_disagreements) <= 10


def test_top_k_entries_sorted_by_delta_descending():
    compare = make_array_comparator(tolerance=AbsoluteTolerance(atol=1e-6), return_diagnostics=True)
    # Disagreements: index 0 → delta 10, index 1 → delta 5, index 2 → delta 1
    a = _array_token([0.0, 0.0, 0.0])
    b = _array_token([10.0, 5.0, 1.0])
    result = compare(a, b)
    deltas = [e[3] if isinstance(e, tuple) else e.delta for e in result.top_k_disagreements]
    assert deltas == sorted(deltas, reverse=True)


def test_top_k_entry_fields_index_expected_actual_delta():
    compare = make_array_comparator(tolerance=AbsoluteTolerance(atol=1e-6), return_diagnostics=True)
    a = _array_token([1.0])
    b = _array_token([4.0])
    result = compare(a, b)
    assert len(result.top_k_disagreements) == 1
    entry = result.top_k_disagreements[0]
    if isinstance(entry, tuple):
        idx, expected, actual, delta = entry
    else:
        idx, expected, actual, delta = entry.index, entry.expected, entry.actual, entry.delta
    assert idx == 0
    assert expected == 1.0
    assert actual == 4.0
    assert delta == 3.0


def test_passing_array_has_empty_top_k():
    compare = make_array_comparator(tolerance=AbsoluteTolerance(atol=1.0), return_diagnostics=True)
    a = _array_token([1.0, 2.0, 3.0])
    b = _array_token([1.0, 2.0, 3.0])
    result = compare(a, b)
    assert result.top_k_disagreements == []


def test_k_default_is_five():
    compare_no_k = make_array_comparator(
        tolerance=AbsoluteTolerance(atol=1e-6), return_diagnostics=True
    )
    a = _array_token([0.0] * 100)
    b = _array_token([float(i) for i in range(100)])
    result = compare_no_k(a, b)
    # Default K must be 5
    assert len(result.top_k_disagreements) == 5


def test_fewer_disagreements_than_k_returns_all():
    compare = make_array_comparator(
        tolerance=AbsoluteTolerance(atol=1e-6), k=10, return_diagnostics=True
    )
    a = _array_token([0.0, 0.0, 0.0])
    b = _array_token([1.0, 2.0, 3.0])
    result = compare(a, b)
    # Only 3 disagreements, k=10 → return all 3
    assert len(result.top_k_disagreements) == 3
