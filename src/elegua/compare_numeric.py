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
        # Finite (numeric) samples
        index_a = {
            _sample_key(s): s["value"]
            for s in samples_a
            if "value" in s and isinstance(s["value"], (int, float))
        }
        index_b = {
            _sample_key(s): s["value"]
            for s in samples_b
            if "value" in s and isinstance(s["value"], (int, float))
        }

        # Non-finite sample keys (flagged as non_finite)
        non_finite_a = {_sample_key(s) for s in samples_a if s.get("non_finite")}
        non_finite_b = {_sample_key(s) for s in samples_b if s.get("non_finite")}

        # Keys present on both sides (either finite or non-finite)
        finite_keys_a = set(index_a)
        finite_keys_b = set(index_b)
        all_keys_a = finite_keys_a | non_finite_a
        all_keys_b = finite_keys_b | non_finite_b
        common_keys = all_keys_a & all_keys_b

        if len(common_keys) < min_samples:
            return TaskStatus.MATH_MISMATCH

        # Check all common points agree
        for key in common_keys:
            in_a_finite = key in index_a
            in_b_finite = key in index_b
            in_a_nf = key in non_finite_a
            in_b_nf = key in non_finite_b

            if in_a_finite and in_b_finite:
                # Both finite — compare within tolerance
                if abs(index_a[key] - index_b[key]) > tol:
                    return TaskStatus.MATH_MISMATCH
            elif in_a_nf and in_b_nf:
                # Both non-finite — agreement
                continue
            elif (in_a_finite or in_a_nf) and (in_b_finite or in_b_nf):
                # One finite, one non-finite at same point — mismatch
                return TaskStatus.MATH_MISMATCH
            else:
                # Point exists on one side only — insufficient to disagree
                continue

        return TaskStatus.OK

    return compare
