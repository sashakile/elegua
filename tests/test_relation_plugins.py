"""Red-phase tests for built-in relation plugins (elegua-779).

These tests define the contract for the future ``elegua.relations`` module.
They should fail until elegua-pvr is implemented.
"""

from __future__ import annotations

import pytest

pytest.importorskip(
    "elegua.relations",
    reason="elegua.relations not yet implemented (elegua-pvr)",
)

from elegua.models import ValidationToken
from elegua.relations import (
    ConvergenceResidualPlugin,
    EqualityPlugin,
    LinearCombinationPlugin,
    NumericalDerivativePlugin,
)
from elegua.task import TaskStatus


def _token(result: dict | None = None, status: TaskStatus = TaskStatus.OK) -> ValidationToken:
    return ValidationToken(adapter_id="test", status=status, result=result)


# --- EqualityPlugin ---


def test_equality_plugin_passthrough_residual_on_equal_tokens():
    plugin = EqualityPlugin()
    a = _token({"value": 1.0})
    b = _token({"value": 1.0})
    residual = plugin.compute(a, b)
    assert isinstance(residual, ValidationToken)
    assert residual.status == TaskStatus.OK


def test_equality_plugin_residual_signals_mismatch_on_unequal():
    plugin = EqualityPlugin()
    a = _token({"value": 1.0})
    b = _token({"value": 2.0})
    residual = plugin.compute(a, b)
    assert isinstance(residual, ValidationToken)
    assert residual.status == TaskStatus.MATH_MISMATCH


def test_equality_plugin_residual_carries_result_payload():
    plugin = EqualityPlugin()
    a = _token({"value": 3.0})
    b = _token({"value": 3.0})
    residual = plugin.compute(a, b)
    assert residual.result is not None
    assert residual.result.get("value") == 3.0


# --- LinearCombinationPlugin ---


def test_linear_combination_produces_synthetic_token():
    plugin = LinearCombinationPlugin(coefficients={"a": 1.0, "b": -1.0})
    tokens = {
        "a": _token({"value": 5.0}),
        "b": _token({"value": 3.0}),
    }
    residual = plugin.compute(tokens)
    assert isinstance(residual, ValidationToken)


def test_linear_combination_residual_reflects_weighted_sum():
    # a=5, b=3; 1.0*5 + (-1.0)*3 = 2.0
    plugin = LinearCombinationPlugin(coefficients={"a": 1.0, "b": -1.0})
    tokens = {
        "a": _token({"value": 5.0}),
        "b": _token({"value": 3.0}),
    }
    residual = plugin.compute(tokens)
    assert residual.result is not None
    assert abs(residual.result["value"] - 2.0) < 1e-9


def test_linear_combination_near_zero_result_is_ok():
    # a=5, b=5; 1.0*5 + (-1.0)*5 = 0.0 -> should agree
    plugin = LinearCombinationPlugin(coefficients={"a": 1.0, "b": -1.0})
    tokens = {
        "a": _token({"value": 5.0}),
        "b": _token({"value": 5.0}),
    }
    residual = plugin.compute(tokens)
    assert residual.status == TaskStatus.OK


# --- NumericalDerivativePlugin ---


def test_numerical_derivative_produces_synthetic_token():
    # h is a construction-time config; compute() receives the two tokens
    # already evaluated at x and x+h — it does not re-apply h itself.
    plugin = NumericalDerivativePlugin(h=1e-5)
    # f(x) = x^2, f'(1.0) ≈ 2.0
    token_at_x = _token({"value": 1.0**2})
    token_at_xph = _token({"value": (1.0 + 1e-5) ** 2})
    residual = plugin.compute(token_at_x, token_at_xph)
    assert isinstance(residual, ValidationToken)


def test_numerical_derivative_residual_approximates_derivative():
    # f(x) = x^2, f'(1.0) = 2.0
    h = 1e-5
    plugin = NumericalDerivativePlugin(h=h)
    token_at_x = _token({"value": 1.0**2})
    token_at_xph = _token({"value": (1.0 + h) ** 2})
    residual = plugin.compute(token_at_x, token_at_xph)
    assert residual.result is not None
    assert abs(residual.result["value"] - 2.0) < 1e-4


# --- ConvergenceResidualPlugin ---


def test_convergence_residual_produces_synthetic_token():
    # ConvergenceResidualPlugin.compute() takes pre-computed error and level
    # lists (not ValidationTokens) — it is a post-processing step that fits
    # the convergence rate and emits a synthetic token summarising the result.
    plugin = ConvergenceResidualPlugin(expected_rate=2.0)
    errors = [0.01, 0.0025, 0.000625]  # h^2 at h=0.1, 0.05, 0.025
    levels = [0.1, 0.05, 0.025]
    residual = plugin.compute(errors=errors, levels=levels)
    assert isinstance(residual, ValidationToken)


def test_convergence_residual_ok_when_rate_matches():
    plugin = ConvergenceResidualPlugin(expected_rate=2.0)
    errors = [0.01, 0.0025, 0.000625]
    levels = [0.1, 0.05, 0.025]
    residual = plugin.compute(errors=errors, levels=levels)
    assert residual.status == TaskStatus.OK


def test_convergence_residual_mismatch_when_rate_wrong():
    plugin = ConvergenceResidualPlugin(expected_rate=4.0)  # require quartic
    errors = [0.01, 0.0025, 0.000625]  # only quadratic
    levels = [0.1, 0.05, 0.025]
    residual = plugin.compute(errors=errors, levels=levels)
    assert residual.status == TaskStatus.MATH_MISMATCH


def test_convergence_residual_carries_fitted_rate_in_result():
    plugin = ConvergenceResidualPlugin(expected_rate=2.0)
    errors = [0.01, 0.0025, 0.000625]
    levels = [0.1, 0.05, 0.025]
    residual = plugin.compute(errors=errors, levels=levels)
    assert residual.result is not None
    assert "fitted_rate" in residual.result
