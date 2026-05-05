"""Array elementwise comparison with diagnostic reporting."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from elegua.models import ValidationToken
from elegua.numeric.tolerance import ToleranceStrategy
from elegua.task import TaskStatus

_DEFAULT_K = 5


@dataclass
class DisagreementEntry:
    index: int
    expected: float
    actual: float
    delta: float


@dataclass
class ArrayComparisonResult:
    status: TaskStatus
    max_disagreement: float = 0.0
    argmax_location: int = 0
    failing_count: int = 0
    top_k_disagreements: list[DisagreementEntry] = field(default_factory=list)


ArrayComparator = Callable[
    [ValidationToken, ValidationToken],
    TaskStatus | ArrayComparisonResult,
]


def make_array_comparator(
    tolerance: ToleranceStrategy,
    *,
    k: int = _DEFAULT_K,
    return_diagnostics: bool = False,
) -> ArrayComparator:
    """Return a token-level comparator for numeric arrays."""

    def compare(
        token_a: ValidationToken, token_b: ValidationToken
    ) -> TaskStatus | ArrayComparisonResult:
        result_a = token_a.result or {}
        result_b = token_b.result or {}

        values_a = result_a.get("values")
        values_b = result_b.get("values")

        if values_a is None or values_b is None:
            if return_diagnostics:
                return ArrayComparisonResult(status=TaskStatus.MATH_MISMATCH)
            return TaskStatus.MATH_MISMATCH

        if len(values_a) != len(values_b):
            if return_diagnostics:
                return ArrayComparisonResult(status=TaskStatus.MATH_MISMATCH)
            return TaskStatus.MATH_MISMATCH

        disagreements: list[DisagreementEntry] = []
        for i, (a, b) in enumerate(zip(values_a, values_b, strict=True)):
            if not tolerance.is_close(a, b):
                disagreements.append(DisagreementEntry(i, a, b, abs(a - b)))

        if not return_diagnostics:
            return TaskStatus.OK if not disagreements else TaskStatus.MATH_MISMATCH

        if not disagreements:
            return ArrayComparisonResult(status=TaskStatus.OK, top_k_disagreements=[])

        disagreements.sort(key=lambda e: e.delta, reverse=True)
        top_k = disagreements[:k]
        max_entry = disagreements[0]

        return ArrayComparisonResult(
            status=TaskStatus.MATH_MISMATCH,
            max_disagreement=max_entry.delta,
            argmax_location=max_entry.index,
            failing_count=len(disagreements),
            top_k_disagreements=top_k,
        )

    return compare
