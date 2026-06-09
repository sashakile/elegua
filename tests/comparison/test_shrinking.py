"""Red-phase tests for disagreement minimization via Hypothesis shrinking (elegua-6yqy).

These tests define the contract for the future ``elegua.comparison.shrinking``
module. They should fail until the feature is implemented (elegua-1v4x).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pytest

pytest.importorskip(
    "elegua.comparison.shrinking",
    reason="elegua.comparison.shrinking not yet implemented (elegua-1v4x)",
)

from elegua.comparison.shrinking import DisagreementMinimizer, MinimizedDisagreement


@runtime_checkable
class _ScalarRunnable(Protocol):
    """Minimal protocol expected by DisagreementMinimizer."""

    adapter_id: str

    def run(self, value: float) -> float: ...


class _DoubleAdapter:
    adapter_id = "double"

    def run(self, value: float) -> float:
        return value * 2.0


class _TripleAdapter:
    """Always disagrees with _DoubleAdapter on non-zero input."""

    adapter_id = "triple"

    def run(self, value: float) -> float:
        return value * 3.0


def test_minimizer_finds_disagreement_for_scalar():
    minimizer = DisagreementMinimizer(adapter_a=_DoubleAdapter(), adapter_b=_TripleAdapter())
    result = minimizer.minimize_scalar(original=100.0)
    assert isinstance(result, MinimizedDisagreement)
    assert result.found


def test_minimized_scalar_is_strictly_simpler_than_original():
    minimizer = DisagreementMinimizer(adapter_a=_DoubleAdapter(), adapter_b=_TripleAdapter())
    result = minimizer.minimize_scalar(original=100.0)
    assert result.found
    assert abs(result.minimal_input) < abs(100.0)


def test_minimizer_reports_adapter_outputs_at_minimal_input():
    minimizer = DisagreementMinimizer(adapter_a=_DoubleAdapter(), adapter_b=_TripleAdapter())
    result = minimizer.minimize_scalar(original=50.0)
    assert result.found
    assert result.output_a != result.output_b


def test_minimizer_returns_not_found_when_adapters_agree():
    minimizer = DisagreementMinimizer(adapter_a=_DoubleAdapter(), adapter_b=_DoubleAdapter())
    result = minimizer.minimize_scalar(original=10.0)
    assert not result.found


def test_minimizer_finds_disagreement_for_array():
    minimizer = DisagreementMinimizer(adapter_a=_DoubleAdapter(), adapter_b=_TripleAdapter())
    result = minimizer.minimize_array(original=[10.0, 20.0, 30.0, 40.0])
    assert isinstance(result, MinimizedDisagreement)
    assert result.found


def test_minimized_array_is_strictly_simpler_than_original():
    minimizer = DisagreementMinimizer(adapter_a=_DoubleAdapter(), adapter_b=_TripleAdapter())
    original = [10.0, 20.0, 30.0, 40.0]
    result = minimizer.minimize_array(original=original)
    assert result.found
    minimal = result.minimal_input
    # Shrinking must strictly reduce complexity in at least one dimension
    fewer_elements = len(minimal) < len(original)
    smaller_magnitude = sum(abs(x) for x in minimal) < sum(abs(x) for x in original)
    assert fewer_elements or smaller_magnitude, (
        f"minimal {minimal!r} is not simpler than original {original!r}"
    )
