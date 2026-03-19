"""Tests for evaluate_expected — verdict logic for test outcomes."""

from __future__ import annotations

from elegua.bridge import Expected, Operation, TestCase
from elegua.isolation import TestRunResult
from elegua.models import ValidationToken
from elegua.task import TaskStatus
from elegua.verdict import evaluate_expected


def _token(repr_val: str = "", **extra: object) -> ValidationToken:
    result: dict = {"repr": repr_val, "type": "Expr"}
    if "properties" in extra:
        result["properties"] = extra.pop("properties")
    return ValidationToken(adapter_id="test", status=TaskStatus.OK, result=result)


def _run_result(
    repr_val: str = "",
    bindings: dict | None = None,
    error: str | None = None,
    **extra: object,
) -> TestRunResult:
    tokens = [_token(repr_val, **extra)] if not error else []
    return TestRunResult(
        test_id="t1",
        tokens=tokens,
        bindings=bindings or {},
        error=error,
    )


def _test_case(expected: Expected | None = None) -> TestCase:
    return TestCase(
        id="t1",
        description="test",
        operations=[Operation(action="Eval")],
        expected=expected,
    )


# --- No expected → pass ---


def test_no_expected_passes():
    result = _run_result("42")
    tc = _test_case(expected=None)
    v = evaluate_expected(result, tc)
    assert v.status == "pass"


# --- Skipped / error passthrough ---


def test_skipped_result():
    result = TestRunResult(test_id="t1", skipped=True, skip_reason="wip")
    tc = _test_case()
    v = evaluate_expected(result, tc)
    assert v.status == "skip"


def test_error_result():
    result = _run_result(error="kernel crash")
    tc = _test_case(Expected(expr="42"))
    v = evaluate_expected(result, tc)
    assert v.status == "error"
    assert "kernel crash" in (v.message or "")


# --- expect_error ---


def test_expect_error_but_succeeded():
    result = _run_result("42")
    tc = _test_case(Expected(expect_error=True))
    v = evaluate_expected(result, tc)
    assert v.status == "fail"
    assert "Expected error" in (v.message or "")


def test_expect_error_and_got_error():
    result = _run_result(error="crash")
    tc = _test_case(Expected(expect_error=True))
    v = evaluate_expected(result, tc)
    assert v.status == "pass"


# --- expr check ---


def test_expr_match():
    result = _run_result("T[-a,-b]")
    tc = _test_case(Expected(expr="T[-a,-b]"))
    v = evaluate_expected(result, tc)
    assert v.status == "pass"


def test_expr_mismatch():
    result = _run_result("T[-a,-b]")
    tc = _test_case(Expected(expr="S[-a,-b]"))
    v = evaluate_expected(result, tc)
    assert v.status == "fail"
    assert v.actual == "T[-a,-b]"
    assert v.expected == "S[-a,-b]"


def test_expr_with_binding_substitution():
    result = _run_result("T[-a,-b]")
    tc = _test_case(Expected(expr="$my_expr"))
    v = evaluate_expected(result, tc, bindings={"my_expr": "T[-a,-b]"})
    assert v.status == "pass"


def test_expr_with_normalizer():
    result = _run_result("  T[-a, -b]  ")
    tc = _test_case(Expected(expr="T[-a,-b]"))
    v = evaluate_expected(result, tc, normalizer=lambda s: s.strip().replace(" ", ""))
    assert v.status == "pass"


# --- normalized check ---


def test_normalized_match():
    result = _run_result("T[-a,-b]")
    tc = _test_case(Expected(normalized="T[-a,-b]"))
    v = evaluate_expected(result, tc)
    assert v.status == "pass"


def test_normalized_mismatch():
    result = _run_result("T[-a,-b]")
    tc = _test_case(Expected(normalized="S[-c,-d]"))
    v = evaluate_expected(result, tc)
    assert v.status == "fail"


def test_normalized_uses_normalizer():
    result = _run_result("  X  ")
    tc = _test_case(Expected(normalized="X"))
    v = evaluate_expected(result, tc, normalizer=str.strip)
    assert v.status == "pass"


# --- is_zero check ---


def test_is_zero_true_and_result_is_zero():
    result = _run_result("0")
    tc = _test_case(Expected(is_zero=True))
    v = evaluate_expected(result, tc)
    assert v.status == "pass"


def test_is_zero_true_but_result_nonzero():
    result = _run_result("T[-a,-b]")
    tc = _test_case(Expected(is_zero=True))
    v = evaluate_expected(result, tc)
    assert v.status == "fail"


def test_is_zero_false_and_result_nonzero():
    result = _run_result("T[-a,-b]")
    tc = _test_case(Expected(is_zero=False))
    v = evaluate_expected(result, tc)
    assert v.status == "pass"


def test_is_zero_with_normalizer():
    result = _run_result("  0  ")
    tc = _test_case(Expected(is_zero=True))
    v = evaluate_expected(result, tc, normalizer=str.strip)
    assert v.status == "pass"


# --- value check ---


def test_value_match():
    result = _run_result("42")
    tc = _test_case(Expected(value=42))
    v = evaluate_expected(result, tc)
    assert v.status == "pass"


def test_value_mismatch():
    result = _run_result("42")
    tc = _test_case(Expected(value=99))
    v = evaluate_expected(result, tc)
    assert v.status == "fail"


def test_value_string_match():
    result = _run_result("hello")
    tc = _test_case(Expected(value="hello"))
    v = evaluate_expected(result, tc)
    assert v.status == "pass"


# --- properties check ---


def test_properties_match():
    result = _run_result("T[-a,-b]", properties={"rank": 2, "type": "Tensor"})
    tc = _test_case(Expected(properties={"rank": 2, "type": "Tensor"}))
    v = evaluate_expected(result, tc)
    assert v.status == "pass"


def test_properties_subset_match():
    """Expected checks only the keys it declares."""
    result = _run_result("T[-a,-b]", properties={"rank": 2, "type": "Tensor", "extra": True})
    tc = _test_case(Expected(properties={"rank": 2}))
    v = evaluate_expected(result, tc)
    assert v.status == "pass"


def test_properties_mismatch():
    result = _run_result("T[-a,-b]", properties={"rank": 1})
    tc = _test_case(Expected(properties={"rank": 2}))
    v = evaluate_expected(result, tc)
    assert v.status == "fail"
    assert "rank" in (v.message or "")


# --- Multiple checks: all must pass ---


def test_multiple_checks_all_pass():
    result = _run_result("0", properties={"rank": 0})
    tc = _test_case(Expected(is_zero=True, properties={"rank": 0}))
    v = evaluate_expected(result, tc)
    assert v.status == "pass"


def test_multiple_checks_first_failure_wins():
    result = _run_result("1")
    tc = _test_case(Expected(is_zero=True, expr="0"))
    v = evaluate_expected(result, tc)
    assert v.status == "fail"


# --- No tokens ---


def test_no_tokens_and_no_expected():
    result = TestRunResult(test_id="t1", tokens=[])
    tc = _test_case(expected=None)
    v = evaluate_expected(result, tc)
    assert v.status == "pass"


def test_no_tokens_but_expected():
    result = TestRunResult(test_id="t1", tokens=[])
    tc = _test_case(Expected(expr="42"))
    v = evaluate_expected(result, tc)
    assert v.status == "error"


# --- Non-dict token.result handling (L9) ---


def test_non_dict_result_uses_str_repr():
    """When token.result is a non-standard object (not dict), use str() for repr.

    ValidationToken.result is typed as dict|None, but verdict code should be
    defensive against receiving unexpected types at runtime.
    """
    token = ValidationToken(adapter_id="test", status=TaskStatus.OK, result=None)
    # Simulate a non-dict result at runtime (bypass Pydantic validation)
    object.__setattr__(token, "result", "raw_string")
    result = TestRunResult(test_id="t1", tokens=[token], bindings={})
    tc = _test_case(Expected(expr="raw_string"))
    v = evaluate_expected(result, tc)
    assert v.status == "pass"
    assert v.actual == "raw_string"


def test_non_dict_result_none_uses_empty_string():
    """When token.result is None, actual_repr should be empty string."""
    token = ValidationToken(adapter_id="test", status=TaskStatus.OK, result=None)
    result = TestRunResult(test_id="t1", tokens=[token], bindings={})
    tc = _test_case(Expected(expr=""))
    v = evaluate_expected(result, tc)
    assert v.status == "pass"
