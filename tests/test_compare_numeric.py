"""Tests for L4 numeric comparison layer — make_numeric_comparator."""

from __future__ import annotations

from elegua.compare_numeric import make_numeric_comparator
from elegua.comparison import ComparisonPipeline
from elegua.models import ValidationToken
from elegua.task import TaskStatus


def _token(result: dict | None = None) -> ValidationToken:
    return ValidationToken(adapter_id="test", status=TaskStatus.OK, result=result)


# --- Matching samples → OK ---


def test_matching_samples_ok():
    compare = make_numeric_comparator(tol=1e-6, min_samples=1)
    a = _token(
        {
            "repr": "x^3/3",
            "numeric_samples": [
                {"vars": {"x": 1.0}, "value": 0.333333},
                {"vars": {"x": 2.0}, "value": 2.666667},
            ],
        }
    )
    b = _token(
        {
            "repr": "Power[x,3]/3",
            "numeric_samples": [
                {"vars": {"x": 1.0}, "value": 0.333333},
                {"vars": {"x": 2.0}, "value": 2.666667},
            ],
        }
    )
    assert compare(a, b) == TaskStatus.OK


def test_matching_within_tolerance():
    compare = make_numeric_comparator(tol=1e-4, min_samples=1)
    a = _token(
        {
            "repr": "x^2",
            "numeric_samples": [{"vars": {"x": 1.0}, "value": 1.00001}],
        }
    )
    b = _token(
        {
            "repr": "x^2",
            "numeric_samples": [{"vars": {"x": 1.0}, "value": 1.00002}],
        }
    )
    assert compare(a, b) == TaskStatus.OK


# --- Divergent samples → MATH_MISMATCH ---


def test_divergent_samples_mismatch():
    compare = make_numeric_comparator(tol=1e-6, min_samples=1)
    a = _token(
        {
            "repr": "x^2",
            "numeric_samples": [{"vars": {"x": 2.0}, "value": 4.0}],
        }
    )
    b = _token(
        {
            "repr": "x^3",
            "numeric_samples": [{"vars": {"x": 2.0}, "value": 8.0}],
        }
    )
    assert compare(a, b) == TaskStatus.MATH_MISMATCH


def test_exceeds_tolerance():
    compare = make_numeric_comparator(tol=1e-6, min_samples=1)
    a = _token(
        {
            "repr": "f(x)",
            "numeric_samples": [{"vars": {"x": 1.0}, "value": 1.0}],
        }
    )
    b = _token(
        {
            "repr": "g(x)",
            "numeric_samples": [{"vars": {"x": 1.0}, "value": 1.001}],
        }
    )
    assert compare(a, b) == TaskStatus.MATH_MISMATCH


# --- Missing/insufficient samples → MATH_MISMATCH ---


def test_no_samples_on_either_side():
    compare = make_numeric_comparator(tol=1e-6, min_samples=1)
    a = _token({"repr": "x^2"})
    b = _token({"repr": "x^2"})
    assert compare(a, b) == TaskStatus.MATH_MISMATCH


def test_samples_on_one_side_only():
    compare = make_numeric_comparator(tol=1e-6, min_samples=1)
    a = _token(
        {
            "repr": "x^2",
            "numeric_samples": [{"vars": {"x": 1.0}, "value": 1.0}],
        }
    )
    b = _token({"repr": "x^2"})
    assert compare(a, b) == TaskStatus.MATH_MISMATCH


def test_insufficient_samples():
    compare = make_numeric_comparator(tol=1e-6, min_samples=3)
    a = _token(
        {
            "repr": "x^2",
            "numeric_samples": [
                {"vars": {"x": 1.0}, "value": 1.0},
                {"vars": {"x": 2.0}, "value": 4.0},
            ],
        }
    )
    b = _token(
        {
            "repr": "x^2",
            "numeric_samples": [
                {"vars": {"x": 1.0}, "value": 1.0},
                {"vars": {"x": 2.0}, "value": 4.0},
            ],
        }
    )
    assert compare(a, b) == TaskStatus.MATH_MISMATCH


def test_empty_samples_list():
    compare = make_numeric_comparator(tol=1e-6, min_samples=1)
    a = _token({"repr": "x", "numeric_samples": []})
    b = _token({"repr": "x", "numeric_samples": []})
    assert compare(a, b) == TaskStatus.MATH_MISMATCH


# --- Pipeline integration ---


def test_registered_as_l4_in_pipeline():
    pipeline = ComparisonPipeline()
    pipeline.register(4, "numeric", make_numeric_comparator(tol=1e-6, min_samples=1))
    assert len(pipeline.layers) == 3
    assert pipeline.layers[-1] == (4, "numeric")


def test_l4_runs_after_l1_l2():
    """L4 catches equivalence that L1/L2 miss (different repr, same numeric values)."""
    pipeline = ComparisonPipeline()
    pipeline.register(4, "numeric", make_numeric_comparator(tol=1e-4, min_samples=1))

    a = _token(
        {
            "repr": "x^3/3",
            "numeric_samples": [
                {"vars": {"x": 1.0}, "value": 0.3333},
                {"vars": {"x": 2.0}, "value": 2.6667},
            ],
        }
    )
    b = _token(
        {
            "repr": "Power[x,3]/3",
            "numeric_samples": [
                {"vars": {"x": 1.0}, "value": 0.3333},
                {"vars": {"x": 2.0}, "value": 2.6667},
            ],
        }
    )
    result = pipeline.compare(a, b)
    assert result.status == TaskStatus.OK
    assert result.layer == 4
    assert result.layer_name == "numeric"


def test_l4_not_reached_if_l2_matches():
    """L4 not called when L2 already matches."""
    pipeline = ComparisonPipeline()
    called = []

    def tracking_numeric(a: ValidationToken, b: ValidationToken) -> TaskStatus:
        called.append(True)
        return TaskStatus.OK

    pipeline.register(4, "numeric", tracking_numeric)

    a = _token({"repr": "x^2", "numeric_samples": [{"vars": {"x": 1.0}, "value": 1.0}]})
    b = _token({"repr": "x^2", "numeric_samples": [{"vars": {"x": 1.0}, "value": 1.0}]})
    result = pipeline.compare(a, b)
    # L1 matches (after stripping numeric_samples, both have {"repr": "x^2"})
    assert result.layer == 1
    assert not called


# --- Multiple sample points ---


def test_multiple_points_all_must_match():
    compare = make_numeric_comparator(tol=1e-6, min_samples=1)
    a = _token(
        {
            "repr": "f",
            "numeric_samples": [
                {"vars": {"x": 1.0}, "value": 1.0},
                {"vars": {"x": 2.0}, "value": 4.0},
                {"vars": {"x": 3.0}, "value": 9.0},
            ],
        }
    )
    b = _token(
        {
            "repr": "g",
            "numeric_samples": [
                {"vars": {"x": 1.0}, "value": 1.0},
                {"vars": {"x": 2.0}, "value": 4.0},
                {"vars": {"x": 3.0}, "value": 10.0},  # diverges here
            ],
        }
    )
    assert compare(a, b) == TaskStatus.MATH_MISMATCH


def test_different_number_of_samples_uses_common():
    """When sample counts differ, compare only common sample points."""
    compare = make_numeric_comparator(tol=1e-6, min_samples=1)
    a = _token(
        {
            "repr": "f",
            "numeric_samples": [
                {"vars": {"x": 1.0}, "value": 1.0},
                {"vars": {"x": 2.0}, "value": 4.0},
            ],
        }
    )
    b = _token(
        {
            "repr": "g",
            "numeric_samples": [
                {"vars": {"x": 1.0}, "value": 1.0},
                {"vars": {"x": 2.0}, "value": 4.0},
                {"vars": {"x": 3.0}, "value": 9.0},
            ],
        }
    )
    # Common points match → OK (min_samples=1 satisfied by 2 common points)
    assert compare(a, b) == TaskStatus.OK


# --- Non-numeric sample values → MATH_MISMATCH (not TypeError) ---


def test_non_numeric_value_string_skipped():
    """Samples with non-numeric 'value' are excluded, not TypeError."""
    compare = make_numeric_comparator(tol=1e-6, min_samples=1)
    a = _token(
        {
            "repr": "f",
            "numeric_samples": [{"vars": {"x": 1.0}, "value": "not-a-number"}],
        }
    )
    b = _token(
        {
            "repr": "g",
            "numeric_samples": [{"vars": {"x": 1.0}, "value": 1.0}],
        }
    )
    # Non-numeric value excluded → no common points → MATH_MISMATCH
    assert compare(a, b) == TaskStatus.MATH_MISMATCH


def test_non_numeric_value_none_skipped():
    """Samples with None 'value' are excluded."""
    compare = make_numeric_comparator(tol=1e-6, min_samples=1)
    a = _token(
        {
            "repr": "f",
            "numeric_samples": [{"vars": {"x": 1.0}, "value": None}],
        }
    )
    b = _token(
        {
            "repr": "g",
            "numeric_samples": [{"vars": {"x": 1.0}, "value": 1.0}],
        }
    )
    assert compare(a, b) == TaskStatus.MATH_MISMATCH


# --- Non-finite sample handling (F12 fix) ---


def test_both_nan_at_same_point_is_agreement():
    """Both sides non-finite at same point → OK (agree on being non-finite)."""
    compare = make_numeric_comparator(tol=1e-6, min_samples=1)
    a = _token(
        {
            "repr": "log(x)",
            "numeric_samples": [
                {"vars": {"x": 0.0}, "value": None, "non_finite": True},
            ],
        }
    )
    b = _token(
        {
            "repr": "log(x)",
            "numeric_samples": [
                {"vars": {"x": 0.0}, "value": None, "non_finite": True},
            ],
        }
    )
    assert compare(a, b) == TaskStatus.OK


def test_one_nan_one_finite_is_mismatch():
    """Same point: one non-finite, one finite → MATH_MISMATCH."""
    compare = make_numeric_comparator(tol=1e-6, min_samples=1)
    a = _token(
        {
            "repr": "f",
            "numeric_samples": [
                {"vars": {"x": 0.0}, "value": None, "non_finite": True},
            ],
        }
    )
    b = _token(
        {
            "repr": "g",
            "numeric_samples": [
                {"vars": {"x": 0.0}, "value": 1.0},
            ],
        }
    )
    assert compare(a, b) == TaskStatus.MATH_MISMATCH


def test_nan_on_one_side_other_side_missing_point():
    """Non-finite on one side, no matching point on other side → MATH_MISMATCH."""
    compare = make_numeric_comparator(tol=1e-6, min_samples=1)
    a = _token(
        {
            "repr": "f",
            "numeric_samples": [
                {"vars": {"x": 0.0}, "value": None, "non_finite": True},
            ],
        }
    )
    b = _token(
        {
            "repr": "g",
            "numeric_samples": [
                {"vars": {"x": 1.0}, "value": 1.0},
            ],
        }
    )
    assert compare(a, b) == TaskStatus.MATH_MISMATCH


def test_all_nan_both_sides_not_false_ok():
    """All points non-finite on both sides → OK (they agree at every point)."""
    compare = make_numeric_comparator(tol=1e-6, min_samples=1)
    a = _token(
        {
            "repr": "f",
            "numeric_samples": [
                {"vars": {"x": 0.0}, "value": None, "non_finite": True},
                {"vars": {"x": 1.0}, "value": None, "non_finite": True},
            ],
        }
    )
    b = _token(
        {
            "repr": "g",
            "numeric_samples": [
                {"vars": {"x": 0.0}, "value": None, "non_finite": True},
                {"vars": {"x": 1.0}, "value": None, "non_finite": True},
            ],
        }
    )
    assert compare(a, b) == TaskStatus.OK


def test_mixed_nan_and_finite_matching():
    """Some non-finite, some finite — all must agree."""
    compare = make_numeric_comparator(tol=1e-6, min_samples=1)
    a = _token(
        {
            "repr": "f",
            "numeric_samples": [
                {"vars": {"x": 0.0}, "value": None, "non_finite": True},
                {"vars": {"x": 1.0}, "value": 1.0},
            ],
        }
    )
    b = _token(
        {
            "repr": "g",
            "numeric_samples": [
                {"vars": {"x": 0.0}, "value": None, "non_finite": True},
                {"vars": {"x": 1.0}, "value": 1.0},
            ],
        }
    )
    assert compare(a, b) == TaskStatus.OK


def test_mixed_nan_finite_mismatch_at_finite_point():
    """Non-finite matches, but finite point diverges → MATH_MISMATCH."""
    compare = make_numeric_comparator(tol=1e-6, min_samples=1)
    a = _token(
        {
            "repr": "f",
            "numeric_samples": [
                {"vars": {"x": 0.0}, "value": None, "non_finite": True},
                {"vars": {"x": 1.0}, "value": 1.0},
            ],
        }
    )
    b = _token(
        {
            "repr": "g",
            "numeric_samples": [
                {"vars": {"x": 0.0}, "value": None, "non_finite": True},
                {"vars": {"x": 1.0}, "value": 2.0},
            ],
        }
    )
    assert compare(a, b) == TaskStatus.MATH_MISMATCH


def test_mixed_non_numeric_and_numeric_values():
    """Only numeric samples participate in comparison."""
    compare = make_numeric_comparator(tol=1e-6, min_samples=1)
    a = _token(
        {
            "repr": "f",
            "numeric_samples": [
                {"vars": {"x": 1.0}, "value": "bad"},
                {"vars": {"x": 2.0}, "value": 4.0},
            ],
        }
    )
    b = _token(
        {
            "repr": "g",
            "numeric_samples": [
                {"vars": {"x": 1.0}, "value": 1.0},
                {"vars": {"x": 2.0}, "value": 4.0},
            ],
        }
    )
    # x=1.0 excluded from a (non-numeric), x=2.0 matches → OK
    assert compare(a, b) == TaskStatus.OK
