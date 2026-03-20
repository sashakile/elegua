"""L4 numeric comparison — sample-point agreement within tolerance.

Factory function that creates a LayerFn closure capturing tolerance
and minimum sample count configuration. Register the returned function
as Layer 4 in a ComparisonPipeline.
"""

from __future__ import annotations

from typing import Any

from elegua.comparison import LayerFn
from elegua.models import ValidationToken
from elegua.task import TaskStatus


def _extract_samples(result: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Extract numeric_samples from a token result, defaulting to empty list."""
    if result is None:
        return []
    samples = result.get("numeric_samples")
    if not isinstance(samples, list):
        return []
    return samples


def _sample_key(sample: dict[str, Any]) -> tuple[tuple[str, float], ...]:
    """Create a hashable key from the vars dict for matching sample points."""
    vars_dict = sample.get("vars", {})
    return tuple(sorted(vars_dict.items()))


def make_numeric_comparator(tol: float = 1e-6, min_samples: int = 1) -> LayerFn:
    """Create an L4 numeric comparison function.

    The returned function compares ``numeric_samples`` from both tokens:
    matching sample points (by variable values) must agree within ``tol``.
    Returns MATH_MISMATCH if fewer than ``min_samples`` common points exist.

    Parameters:
        tol: Absolute tolerance for value comparison.
        min_samples: Minimum number of common sample points required.
    """

    def compare(token_a: ValidationToken, token_b: ValidationToken) -> TaskStatus:
        samples_a = _extract_samples(token_a.result)
        samples_b = _extract_samples(token_b.result)

        # Index samples by their variable-value key
        index_a = {_sample_key(s): s["value"] for s in samples_a if "value" in s}
        index_b = {_sample_key(s): s["value"] for s in samples_b if "value" in s}

        # Find common sample points
        common_keys = set(index_a) & set(index_b)

        if len(common_keys) < min_samples:
            return TaskStatus.MATH_MISMATCH

        # Check all common points agree within tolerance
        for key in common_keys:
            if abs(index_a[key] - index_b[key]) > tol:
                return TaskStatus.MATH_MISMATCH

        return TaskStatus.OK

    return compare
