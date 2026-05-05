"""Red-phase tests for scalar tolerance strategies and profile-resolved comparisons.

All tests in this file MUST FAIL until elegua.numeric.tolerance is implemented.
See: elegua-io8, elegua-d5m.
"""

from __future__ import annotations

import struct

import pytest

pytest.importorskip(
    "elegua.numeric.tolerance",
    reason="elegua.numeric not yet implemented (elegua-d5m)",
)

from elegua.models import ValidationToken
from elegua.numeric.tolerance import (
    AbsoluteTolerance,
    MixedTolerance,
    RelativeTolerance,
    StochasticTolerance,
    ToleranceProfile,
    ULPTolerance,
    make_scalar_comparator,
)
from elegua.task import TaskStatus


def _scalar_token(
    value: float,
    standard_error: float | None = None,
    quantity_label: str | None = None,
) -> ValidationToken:
    result: dict = {"value": value}
    if standard_error is not None:
        result["standard_error"] = standard_error
    if quantity_label is not None:
        result["quantity_label"] = quantity_label
    return ValidationToken(adapter_id="test", status=TaskStatus.OK, result=result)


# --- AbsoluteTolerance ---


def test_absolute_tolerance_passes_within_atol():
    tol = AbsoluteTolerance(atol=1e-6)
    assert tol.is_close(1.0, 1.0 + 5e-7) is True


def test_absolute_tolerance_fails_beyond_atol():
    tol = AbsoluteTolerance(atol=1e-6)
    assert tol.is_close(1.0, 1.0 + 2e-6) is False


def test_absolute_tolerance_exact_boundary_passes():
    tol = AbsoluteTolerance(atol=1e-6)
    assert tol.is_close(0.0, 1e-6) is True


def test_absolute_tolerance_symmetric():
    tol = AbsoluteTolerance(atol=1e-4)
    assert tol.is_close(1.0, 0.9999) == tol.is_close(0.9999, 1.0)


# --- RelativeTolerance ---


def test_relative_tolerance_passes_within_rtol():
    tol = RelativeTolerance(rtol=1e-4)
    # |2.0 - 2.0002| = 2e-4 <= 1e-4 * max(2.0, 2.0002) ≈ 2e-4 exactly
    assert tol.is_close(2.0, 2.0002) is True


def test_relative_tolerance_fails_beyond_rtol():
    tol = RelativeTolerance(rtol=1e-6)
    assert tol.is_close(1.0, 1.0 + 1e-4) is False


def test_relative_tolerance_uses_max_of_magnitudes():
    # For large values, rtol * max(|a|, |b|) gives larger absolute tolerance
    tol = RelativeTolerance(rtol=1e-3)
    assert tol.is_close(1000.0, 1000.5) is True  # |diff| = 0.5 <= 1e-3 * 1000.5


def test_relative_tolerance_near_zero_uses_larger():
    tol = RelativeTolerance(rtol=1e-3)
    # Both near zero: rtol * max ≈ 0 → tiny tolerance
    assert tol.is_close(0.0, 1e-10) is True
    assert tol.is_close(0.0, 1.0) is False


# --- MixedTolerance ---


def test_mixed_tolerance_passes_within_atol_plus_rtol():
    tol = MixedTolerance(atol=1e-8, rtol=1e-6)
    a, b = 100.0, 100.0 + 1e-4
    expected_threshold = 1e-8 + 1e-6 * max(abs(a), abs(b))
    assert abs(a - b) <= expected_threshold
    assert tol.is_close(a, b) is True


def test_mixed_tolerance_fails_when_both_exceeded():
    tol = MixedTolerance(atol=1e-10, rtol=1e-10)
    assert tol.is_close(1.0, 1.1) is False


def test_mixed_tolerance_atol_saves_small_values():
    # Near zero: rtol contribution is tiny, atol is the floor
    tol = MixedTolerance(atol=1e-6, rtol=1e-3)
    assert tol.is_close(0.0, 5e-7) is True  # within atol alone
    assert tol.is_close(0.0, 2e-6) is False  # exceeds atol with no rtol contribution


def test_mixed_tolerance_rtol_saves_large_values():
    tol = MixedTolerance(atol=1e-8, rtol=1e-4)
    # For large values, rtol contribution dominates
    assert tol.is_close(1e6, 1e6 + 50.0) is True  # 50 <= 1e-4 * 1e6 = 100


# --- ULPTolerance ---


def _ulp_neighbors(value: float, n: int) -> float:
    """Return the float that is exactly n ULPs away from value."""
    packed = struct.pack(">d", value)
    bits = int.from_bytes(packed, "big")
    bits += n
    return struct.unpack(">d", bits.to_bytes(8, "big"))[0]


def test_ulp_tolerance_passes_within_n_ulps():
    tol = ULPTolerance(n_ulps=4)
    a = 1.0
    b = _ulp_neighbors(a, 3)
    assert tol.is_close(a, b) is True


def test_ulp_tolerance_fails_beyond_n_ulps():
    tol = ULPTolerance(n_ulps=4)
    a = 1.0
    b = _ulp_neighbors(a, 10)
    assert tol.is_close(a, b) is False


def test_ulp_tolerance_exact_boundary():
    tol = ULPTolerance(n_ulps=2)
    a = 1.0
    b = _ulp_neighbors(a, 2)
    assert tol.is_close(a, b) is True


def test_ulp_tolerance_symmetric():
    tol = ULPTolerance(n_ulps=3)
    a = 2.0
    b = _ulp_neighbors(a, 5)
    assert tol.is_close(a, b) == tol.is_close(b, a)


# --- StochasticTolerance ---


def test_stochastic_tolerance_passes_within_k_se():
    # k=3, se_a=0.1, se_b=0.0 → threshold = 3 * sqrt(0.01) = 0.3
    tol = StochasticTolerance(k=3.0)
    assert tol.is_close(1.0, 1.2, se_a=0.1, se_b=0.0) is True


def test_stochastic_tolerance_fails_beyond_k_se():
    tol = StochasticTolerance(k=3.0)
    # threshold = 3 * sqrt(0.01 + 0.01) ≈ 0.424; diff = 1.0 > 0.424
    assert tol.is_close(0.0, 1.0, se_a=0.1, se_b=0.1) is False


def test_stochastic_tolerance_missing_se_treated_as_exact():
    # Missing se → se=0 for that side → threshold = k * |se_other|
    tol = StochasticTolerance(k=3.0)
    # se_a=0, se_b=0 → threshold = 0 → must be exact
    assert tol.is_close(1.0, 1.0, se_a=0.0, se_b=0.0) is True
    assert tol.is_close(1.0, 1.0 + 1e-15, se_a=0.0, se_b=0.0) is False


def test_stochastic_tolerance_combined_se():
    tol = StochasticTolerance(k=2.0)
    se_a, se_b = 0.3, 0.4
    # threshold = 2.0 * math.sqrt(se_a**2 + se_b**2) = 2 * 0.5 = 1.0
    assert tol.is_close(0.0, 0.99, se_a=se_a, se_b=se_b) is True
    assert tol.is_close(0.0, 1.01, se_a=se_a, se_b=se_b) is False


# --- ToleranceProfile ---


def test_profile_resolves_strategy_by_quantity_label():
    profile = ToleranceProfile()
    profile.register("price", MixedTolerance(atol=1e-4, rtol=1e-6))
    strategy = profile.get("price")
    assert strategy.is_close(100.0, 100.0 + 5e-5) is True


def test_profile_missing_label_raises():
    profile = ToleranceProfile()
    with pytest.raises(KeyError):
        profile.get("nonexistent_quantity")


def test_profile_multiple_quantities():
    profile = ToleranceProfile()
    profile.register("price", AbsoluteTolerance(atol=1e-4))
    profile.register("rate", RelativeTolerance(rtol=1e-3))
    assert profile.get("price").is_close(1.0, 1.00005) is True
    assert profile.get("rate").is_close(1.0, 1.0005) is True


# --- make_scalar_comparator (token-level) ---


def test_scalar_comparator_atol_ok():
    compare = make_scalar_comparator(strategy=AbsoluteTolerance(atol=1e-4))
    assert compare(_scalar_token(1.0), _scalar_token(1.00005)) == TaskStatus.OK


def test_scalar_comparator_atol_mismatch():
    compare = make_scalar_comparator(strategy=AbsoluteTolerance(atol=1e-6))
    assert compare(_scalar_token(1.0), _scalar_token(2.0)) == TaskStatus.MATH_MISMATCH


def test_scalar_comparator_mixed_ok():
    compare = make_scalar_comparator(strategy=MixedTolerance(atol=1e-8, rtol=1e-4))
    assert compare(_scalar_token(1000.0), _scalar_token(1000.05)) == TaskStatus.OK


def test_scalar_comparator_missing_value_is_mismatch():
    compare = make_scalar_comparator(strategy=AbsoluteTolerance(atol=1e-6))
    no_value = ValidationToken(adapter_id="test", status=TaskStatus.OK, result={})
    assert compare(no_value, _scalar_token(1.0)) == TaskStatus.MATH_MISMATCH


def test_scalar_comparator_stochastic_uses_standard_error():
    compare = make_scalar_comparator(strategy=StochasticTolerance(k=3.0))
    a = _scalar_token(1.0, standard_error=0.1)
    b = _scalar_token(1.2, standard_error=0.0)
    assert compare(a, b) == TaskStatus.OK  # |diff|=0.2 <= 3*0.1


def test_scalar_comparator_profile_resolved():
    profile = ToleranceProfile()
    profile.register("vega", AbsoluteTolerance(atol=1e-3))
    compare = make_scalar_comparator(profile=profile)
    a = _scalar_token(0.5, quantity_label="vega")
    b = _scalar_token(0.5005, quantity_label="vega")
    assert compare(a, b) == TaskStatus.OK


def test_scalar_comparator_profile_missing_label_is_error():
    profile = ToleranceProfile()
    compare = make_scalar_comparator(profile=profile)
    a = _scalar_token(1.0, quantity_label="unknown_qty")
    b = _scalar_token(1.0, quantity_label="unknown_qty")
    result = compare(a, b)
    assert result == TaskStatus.EXECUTION_ERROR
