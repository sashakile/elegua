"""Verdict evaluation — compare test results against expected outcomes.

Standalone function that evaluates a TestRunResult against its TestCase
expected block. Domain-specific normalization is injectable.

Usage::

    verdict = evaluate_expected(result, test_case, normalizer=my_normalize)
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from elegua.bridge import TestCase
from elegua.isolation import TestRunResult

_REF_RE = re.compile(r"\$(\w+)")


@dataclass(frozen=True)
class Verdict:
    """Outcome of evaluating a test against its expected values."""

    __test__ = False

    status: Literal["pass", "fail", "skip", "error"]
    actual: str | None = None
    expected: str | None = None
    message: str | None = None


def evaluate_expected(
    result: TestRunResult,
    test_case: TestCase,
    bindings: dict[str, str] | None = None,
    normalizer: Callable[[str], str] | None = None,
) -> Verdict:
    """Evaluate a test result against its expected outcome.

    Parameters:
        result: The execution result from IsolatedRunner.
        test_case: The test case with optional Expected block.
        bindings: Variable bindings for $-substitution in expected.expr.
            Defaults to result.bindings if not provided.
        normalizer: Optional function to normalize expression strings
            before comparison. Domain-specific (injected by caller).
    """
    if result.skipped:
        return Verdict(status="skip", message=result.skip_reason)

    if bindings is None:
        bindings = result.bindings

    exp = test_case.expected

    # No expected → pass (execution-only test)
    if exp is None:
        return Verdict(status="pass")

    # expect_error handling
    if exp.expect_error:
        if result.error:
            return Verdict(status="pass", message=result.error)
        return Verdict(status="fail", message="Expected error but operation succeeded")

    # Execution error with no expect_error → propagate
    if result.error:
        return Verdict(status="error", message=result.error)

    # Need a token to evaluate against
    if not result.tokens:
        return Verdict(status="error", message="No tokens produced")

    last_token = result.tokens[-1]
    token_result = last_token.result or {}
    if isinstance(token_result, dict):
        actual_repr = token_result.get("repr", "")
    else:
        actual_repr = str(token_result) if token_result else ""

    norm = normalizer or _identity

    # --- expr check ---
    if exp.expr is not None:
        expected_expr = _sub_refs(exp.expr, bindings)
        if norm(actual_repr) != norm(expected_expr):
            return Verdict(
                status="fail",
                actual=actual_repr,
                expected=expected_expr,
                message=f"Expression mismatch: got {actual_repr!r}, expected {expected_expr!r}",
            )

    # --- normalized check ---
    if exp.normalized is not None and norm(actual_repr) != exp.normalized:
        return Verdict(
            status="fail",
            actual=norm(actual_repr),
            expected=exp.normalized,
            message=(
                f"Normalized mismatch: got {norm(actual_repr)!r}, expected {exp.normalized!r}"
            ),
        )

    # --- is_zero check ---
    if exp.is_zero is not None:
        actually_zero = norm(actual_repr) == norm("0")
        if actually_zero != exp.is_zero:
            return Verdict(
                status="fail",
                actual=actual_repr,
                message=f"is_zero: expected {exp.is_zero}, got {actually_zero}",
            )

    # --- value check ---
    if exp.value is not None and str(exp.value) != actual_repr:
        return Verdict(
            status="fail",
            actual=actual_repr,
            expected=str(exp.value),
            message=f"Value mismatch: got {actual_repr!r}, expected {exp.value!r}",
        )

    # --- properties check ---
    if exp.properties is not None:
        actual_props: dict[str, Any] = (
            token_result.get("properties", {}) if isinstance(token_result, dict) else {}
        )
        for key, expected_val in exp.properties.items():
            actual_val = actual_props.get(key)
            if actual_val != expected_val:
                return Verdict(
                    status="fail",
                    actual=str(actual_val),
                    expected=str(expected_val),
                    message=f"Property {key!r}: got {actual_val!r}, expected {expected_val!r}",
                )

    return Verdict(status="pass", actual=actual_repr)


def _identity(s: str) -> str:
    return s


def _sub_refs(text: str, bindings: dict[str, str]) -> str:
    return _REF_RE.sub(lambda m: bindings.get(m.group(1), m.group(0)), text)
