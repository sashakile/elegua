"""Red-phase tests for ConvergenceFixture (elegua-2r8).

These tests define the contract for the future ``elegua.convergence`` module.
They should fail until elegua-vyt is implemented.
"""

from __future__ import annotations

import math

import pytest

pytest.importorskip(
    "elegua.convergence",
    reason="elegua.convergence not yet implemented (elegua-vyt)",
)

from elegua.convergence import (
    AdapterReference,
    AnalyticReference,
    ConvergenceFixture,
    ConvergenceReport,
    LiteralReference,
    RichardsonReference,
)

# --- Helpers ---


# f(h) = h^2 exactly -> convergence rate 2.0
def _quadratic(h: float) -> float:
    return h * h


class _ZeroReferenceAdapter:
    """Toy reference adapter: always returns 0.0 (exact solution for _quadratic at h->0)."""

    adapter_id = "zero-reference"

    def run(self, h: float) -> float:
        return 0.0


_LEVELS = (0.1, 0.05, 0.025, 0.0125)


# --- Analytic reference mode ---


def test_analytic_reference_runs_all_levels():
    fixture = ConvergenceFixture(
        levels=_LEVELS,
        reference=AnalyticReference(value=0.0),
        expected_rate=2.0,
    )
    report = fixture.run(_quadratic)
    assert isinstance(report, ConvergenceReport)
    assert len(report.errors) == len(_LEVELS)


def test_analytic_reference_fits_correct_rate():
    fixture = ConvergenceFixture(
        levels=_LEVELS,
        reference=AnalyticReference(value=0.0),
        expected_rate=2.0,
    )
    report = fixture.run(_quadratic)
    assert abs(report.rate - 2.0) < 0.1


def test_analytic_reference_reports_r_squared():
    fixture = ConvergenceFixture(
        levels=_LEVELS,
        reference=AnalyticReference(value=0.0),
        expected_rate=2.0,
    )
    report = fixture.run(_quadratic)
    assert 0.0 <= report.r_squared <= 1.0
    # Perfect power-law convergence -> R^2 very close to 1
    assert report.r_squared > 0.99


def test_analytic_reference_passes_when_rate_matches():
    fixture = ConvergenceFixture(
        levels=_LEVELS,
        reference=AnalyticReference(value=0.0),
        expected_rate=2.0,
    )
    report = fixture.run(_quadratic)
    assert report.passed


# --- Literal reference mode ---


def test_literal_reference_uses_per_level_values():
    # Provide exact analytic values per level (same as AnalyticReference but explicit)
    literal_values = [0.0] * len(_LEVELS)
    fixture = ConvergenceFixture(
        levels=_LEVELS,
        reference=LiteralReference(values=literal_values),
        expected_rate=2.0,
    )
    report = fixture.run(_quadratic)
    assert report.passed


def test_literal_reference_requires_same_count_as_levels():
    with pytest.raises((ValueError, TypeError)):
        ConvergenceFixture(
            levels=_LEVELS,
            reference=LiteralReference(values=[0.0]),  # wrong count
            expected_rate=2.0,
        )


# --- Richardson extrapolation reference mode ---


def test_richardson_reference_extrapolates_from_finest_levels():
    fixture = ConvergenceFixture(
        levels=_LEVELS,
        reference=RichardsonReference(),
        expected_rate=2.0,
    )
    report = fixture.run(_quadratic)
    assert isinstance(report, ConvergenceReport)
    assert report.passed


# --- Failed diagnostics ---


def test_failed_when_rate_below_expected():
    fixture = ConvergenceFixture(
        levels=_LEVELS,
        reference=AnalyticReference(value=0.0),
        expected_rate=3.0,  # require cubic, get quadratic -> fails
    )
    report = fixture.run(_quadratic)
    assert not report.passed


def test_failed_when_r_squared_below_threshold():
    # Noisy function: not a clean power law -> low R^2
    def _noisy(h: float) -> float:
        return h * h + 0.05 * math.sin(1.0 / h)

    fixture = ConvergenceFixture(
        levels=_LEVELS,
        reference=AnalyticReference(value=0.0),
        expected_rate=2.0,
        min_r_squared=0.999,  # very strict threshold
    )
    report = fixture.run(_noisy)
    assert not report.passed


def test_report_includes_rate_and_r_squared_on_failure():
    fixture = ConvergenceFixture(
        levels=_LEVELS,
        reference=AnalyticReference(value=0.0),
        expected_rate=3.0,
    )
    report = fixture.run(_quadratic)
    assert not report.passed
    # Diagnostics must still be present even on failure
    assert isinstance(report.rate, float)
    assert isinstance(report.r_squared, float)


# --- Adapter reference mode ---


def test_adapter_reference_uses_adapter_output_as_reference():
    # AdapterReference calls adapter.run(h) at each level to compute reference values.
    fixture = ConvergenceFixture(
        levels=_LEVELS,
        reference=AdapterReference(adapter=_ZeroReferenceAdapter()),
        expected_rate=2.0,
    )
    report = fixture.run(_quadratic)
    assert isinstance(report, ConvergenceReport)
    assert report.passed
