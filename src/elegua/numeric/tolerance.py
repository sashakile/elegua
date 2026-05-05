"""Scalar tolerance strategies and profile-resolved comparators."""

from __future__ import annotations

import math
import struct
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from elegua.models import ValidationToken
from elegua.task import TaskStatus


class ToleranceStrategy(Protocol):
    def is_close(self, a: float, b: float, **kwargs: Any) -> bool: ...


@dataclass(frozen=True)
class AbsoluteTolerance:
    atol: float

    def is_close(self, a: float, b: float, **_: Any) -> bool:
        return abs(a - b) <= self.atol


@dataclass(frozen=True)
class RelativeTolerance:
    rtol: float

    def is_close(self, a: float, b: float, **_: Any) -> bool:
        # Floor at 1.0 so near-zero values are compared on absolute scale
        return abs(a - b) <= self.rtol * max(abs(a), abs(b), 1.0)


@dataclass(frozen=True)
class MixedTolerance:
    atol: float
    rtol: float

    def is_close(self, a: float, b: float, **_: Any) -> bool:
        return abs(a - b) <= self.atol + self.rtol * max(abs(a), abs(b))


def _to_ordered_int(x: float) -> int:
    """Map a finite float to a monotone integer for ULP arithmetic."""
    if not math.isfinite(x):
        raise ValueError(f"ULP distance undefined for non-finite value: {x!r}")
    n = int.from_bytes(struct.pack(">d", x), "big", signed=False)
    # Negative floats have the sign bit set; flip all bits to make the
    # representation monotone (sign-magnitude → two's-complement style).
    return n if n < (1 << 63) else n - (1 << 64)


def _ulp_distance(a: float, b: float) -> int:
    return abs(_to_ordered_int(a) - _to_ordered_int(b))


@dataclass(frozen=True)
class ULPTolerance:
    n_ulps: int

    def is_close(self, a: float, b: float, **_: Any) -> bool:
        return _ulp_distance(a, b) <= self.n_ulps


@dataclass(frozen=True)
class StochasticTolerance:
    k: float

    def is_close(self, a: float, b: float, se_a: float = 0.0, se_b: float = 0.0, **_: Any) -> bool:
        threshold = self.k * math.sqrt(se_a**2 + se_b**2)
        return abs(a - b) <= threshold


class ToleranceProfile:
    """Registry mapping quantity labels to tolerance strategies."""

    def __init__(self) -> None:
        self._strategies: dict[str, ToleranceStrategy] = {}

    def register(self, label: str, strategy: ToleranceStrategy) -> None:
        self._strategies[label] = strategy

    def get(self, label: str) -> ToleranceStrategy:
        return self._strategies[label]


ScalarComparator = Callable[[ValidationToken, ValidationToken], TaskStatus]


def make_scalar_comparator(
    *,
    strategy: ToleranceStrategy | None = None,
    profile: ToleranceProfile | None = None,
) -> ScalarComparator:
    """Return a token-level comparator using the given strategy or profile."""

    def compare(token_a: ValidationToken, token_b: ValidationToken) -> TaskStatus:
        result_a = token_a.result or {}
        result_b = token_b.result or {}

        if "value" not in result_a or "value" not in result_b:
            return TaskStatus.MATH_MISMATCH

        a: float = result_a["value"]
        b: float = result_b["value"]

        if profile is not None:
            label_a = result_a.get("quantity_label")
            label_b = result_b.get("quantity_label")
            if label_a and label_b and label_a != label_b:
                return TaskStatus.EXECUTION_ERROR
            label = label_a or label_b
            try:
                strategy_ = profile.get(label)  # type: ignore[arg-type]
            except KeyError:
                return TaskStatus.EXECUTION_ERROR
        else:
            strategy_ = strategy

        if strategy_ is None:
            return TaskStatus.EXECUTION_ERROR

        kwargs: dict[str, Any] = {}
        if isinstance(strategy_, StochasticTolerance):
            kwargs["se_a"] = result_a.get("standard_error", 0.0)
            kwargs["se_b"] = result_b.get("standard_error", 0.0)

        return TaskStatus.OK if strategy_.is_close(a, b, **kwargs) else TaskStatus.MATH_MISMATCH

    return compare
