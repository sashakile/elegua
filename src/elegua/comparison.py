"""Layer 1 identity comparison — structural equality of result payloads."""

from __future__ import annotations

from typing import Any

from elegua.task import TaskStatus


def compare_identity(result_a: dict[str, Any], result_b: dict[str, Any]) -> TaskStatus:
    """Return OK if results are structurally equal, MATH_MISMATCH otherwise."""
    if result_a == result_b:
        return TaskStatus.OK
    return TaskStatus.MATH_MISMATCH
