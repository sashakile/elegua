"""Numeric comparison layer factory for ComparisonPipeline.

Register with ``exclude_keys=NUMERIC_KEYS`` at layer 3 so that L1/L2 do not
compare numeric fields; the layer dispatches by payload type instead.
"""

from __future__ import annotations

from elegua.compare_numeric import make_numeric_comparator
from elegua.comparison import LayerFn
from elegua.models import ValidationToken
from elegua.numeric.array import make_array_comparator
from elegua.numeric.tolerance import ToleranceProfile, ToleranceStrategy, make_scalar_comparator
from elegua.task import TaskStatus

NUMERIC_KEYS: frozenset[str] = frozenset(
    {"value", "values", "numeric_samples", "quantity_label", "standard_error"}
)


def make_numeric_layer(
    *,
    strategy: ToleranceStrategy | None = None,
    profile: ToleranceProfile | None = None,
    array_strategy: ToleranceStrategy | None = None,
    tol: float = 1e-6,
    min_samples: int = 1,
    k: int = 5,
) -> LayerFn:
    """Return a LayerFn that routes by numeric payload type.

    Routing (first matching key wins):
    - ``value`` field → scalar comparator (strategy / profile)
    - ``values`` field → array comparator (array_strategy or strategy)
    - ``numeric_samples`` field → sample-point comparator (tol, min_samples)
    - No numeric fields → MATH_MISMATCH (non-opt-in fixtures pass through to L1/L2)
    """
    scalar_cmp = make_scalar_comparator(strategy=strategy, profile=profile)
    _arr_tol = array_strategy or strategy
    array_cmp = make_array_comparator(_arr_tol, k=k) if _arr_tol is not None else None
    samples_cmp = make_numeric_comparator(tol=tol, min_samples=min_samples)

    def compare(token_a: ValidationToken, token_b: ValidationToken) -> TaskStatus:
        ra = token_a.result
        rb = token_b.result

        if ra is not None and "value" in ra and rb is not None and "value" in rb:
            return scalar_cmp(token_a, token_b)

        if ra is not None and "values" in ra and rb is not None and "values" in rb:
            if array_cmp is None:
                return TaskStatus.EXECUTION_ERROR
            result = array_cmp(token_a, token_b)
            return result if isinstance(result, TaskStatus) else result.status

        has_samples = ra is not None and "numeric_samples" in ra
        if has_samples and rb is not None and "numeric_samples" in rb:
            return samples_cmp(token_a, token_b)

        return TaskStatus.MATH_MISMATCH

    return compare
