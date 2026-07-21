# Numeric comparison

**Configure tolerance strategies for scalar, array, and sample-point comparisons, and register them as a pipeline layer.**

> **What it does** — The numeric comparison layer lets you compare floating-point results using configurable tolerance strategies: absolute, relative, mixed, ULP, and stochastic. Array comparisons include top-K diagnostic reporting.  \n> **Use this when** — You need to compare numerical results (not symbolic) where exact structural equality is too strict.  \n> **Prerequisites** — [Comparison pipeline](comparison.md) for how layers work.  \n> **Outcome** — Know how to configure tolerance strategies, create a numeric layer, register it in the pipeline, and interpret diagnostic results.

## Tolerance strategies

All strategies implement the ``ToleranceStrategy`` protocol — a single method ``is_close(a, b, **kwargs) → bool``. Choose the strategy that matches your quantity's error characteristics.

| Strategy | When to use | Key parameter |
|----------|-------------|---------------|
| ``AbsoluteTolerance`` | Error is bounded by a fixed magnitude | ``atol`` |
| ``RelativeTolerance`` | Error scales with value magnitude | ``rtol`` |
| ``MixedTolerance`` | Both absolute and relative components | ``atol`` + ``rtol`` |
| ``ULPTolerance`` | Bit-level precision (floating-point round-off) | ``n_ulps`` |
| ``StochasticTolerance`` | Monte Carlo / noisy estimates with standard error | ``k`` (sigma multiplier) |

### Absolute tolerance

Passes when ``|a - b| <= atol``. Use for quantities with a fixed error budget.

```python
from elegua.numeric.tolerance import AbsoluteTolerance

tol = AbsoluteTolerance(atol=1e-6)
assert tol.is_close(1.000001, 1.0)    # True  (difference 1e-6)
assert not tol.is_close(1.00001, 1.0)  # False (difference 1e-5)
```

### Relative tolerance

Passes when ``|a - b| <= rtol * max(|a|, |b|, 1.0)``. The floor at 1.0 prevents division by near-zero. Use for quantities where error scales with magnitude.

```python
from elegua.numeric.tolerance import RelativeTolerance

tol = RelativeTolerance(rtol=1e-4)
assert tol.is_close(1.0001, 1.0)      # True
assert tol.is_close(1000.1, 1000.0)   # True  (relative error 1e-4)
```

### Mixed tolerance

Passes when ``|a - b| <= atol + rtol * max(|a|, |b|)``. Combines both scales — useful for values that range from near-zero to large.

```python
from elegua.numeric.tolerance import MixedTolerance

tol = MixedTolerance(atol=1e-6, rtol=1e-3)
assert tol.is_close(0.0, 1e-7)        # True  (absolute difference 1e-7)
```

### ULP tolerance

Passes when the integer representations of the two floats differ by at most ``n_ulps``. This is the most precise comparison — it catches only floating-point round-off, not semantic differences.

```python
from elegua.numeric.tolerance import ULPTolerance

tol = ULPTolerance(n_ulps=2)
assert tol.is_close(1.0, 1.0 + 2**-52)  # True  (1 ULP apart)
```

### Stochastic tolerance

Passes when ``|a - b| <= k * sqrt(se_a² + se_b²)``, where ``se`` is the standard error of each estimate. Use for Monte Carlo or noisy results where each value has an associated uncertainty.

```python
from elegua.numeric.tolerance import StochasticTolerance

tol = StochasticTolerance(k=3.0)  # 3-sigma threshold
# The standard_error values come from the token result payload
assert tol.is_close(1.0, 1.05, se_a=0.01, se_b=0.01)
# => True: |1.0 - 1.05| = 0.05 <= 3.0 * sqrt(0.01² + 0.01²) ≈ 0.042
```

## Scalar comparison

### Direct comparison with a fixed strategy

```python
from elegua.numeric.tolerance import AbsoluteTolerance, make_scalar_comparator
from elegua.models import ValidationToken
from elegua.task import TaskStatus

compare = make_scalar_comparator(strategy=AbsoluteTolerance(atol=1e-6))

token_a = ValidationToken(
    adapter_id="oracle",
    status=TaskStatus.OK,
    result={"value": 1.000001},
)
token_b = ValidationToken(
    adapter_id="iut",
    status=TaskStatus.OK,
    result={"value": 1.0},
)

status = compare(token_a, token_b)
assert status == TaskStatus.OK  # within 1e-6 tolerance
```

### Profile-based resolution by quantity label

Use a ``ToleranceProfile`` to apply different strategies to different quantities, resolved by the ``quantity_label`` field in the token result:

```python
from elegua.numeric.tolerance import (
    AbsoluteTolerance,
    RelativeTolerance,
    ToleranceProfile,
    make_scalar_comparator,
)

profile = ToleranceProfile()
profile.register("energy", AbsoluteTolerance(atol=1e-8))
profile.register("rate", RelativeTolerance(rtol=1e-3))

compare = make_scalar_comparator(profile=profile)

token_a = ValidationToken(
    adapter_id="oracle",
    status=TaskStatus.OK,
    result={"value": 1.0, "quantity_label": "energy"},
)
token_b = ValidationToken(
    adapter_id="iut",
    status=TaskStatus.OK,
    result={"value": 1.00000001, "quantity_label": "energy"},
)

assert compare(token_a, token_b) == TaskStatus.OK  # uses AbsoluteTolerance(atol=1e-8)
```

## Array comparison with top-K diagnostics

Compare two arrays elementwise and report the worst disagreements:

```python
from elegua.numeric.tolerance import AbsoluteTolerance
from elegua.numeric.array import make_array_comparator
from elegua.models import ValidationToken
from elegua.task import TaskStatus

comparator = make_array_comparator(
    AbsoluteTolerance(atol=1e-6),
    k=5,                           # report top 5 disagreements
    return_diagnostics=True,
)

token_a = ValidationToken(
    adapter_id="oracle",
    status=TaskStatus.OK,
    result={"values": [1.0, 2.0, 3.0, 4.0, 5.0]},
)
token_b = ValidationToken(
    adapter_id="iut",
    status=TaskStatus.OK,
    result={"values": [1.0, 2.05, 3.0, 4.1, 5.0]},
)

result = comparator(token_a, token_b)
print(result.status)              # TaskStatus.MATH_MISMATCH
print(result.max_disagreement)    # 0.1 (at index 3)
print(result.argmax_location)     # 3
print(result.failing_count)       # 2
for entry in result.top_k_disagreements:
    print(f"  index {entry.index}: expected {entry.expected}, got {entry.actual}")
# => index 3: expected 4.0, got 4.1
# => index 1: expected 2.0, got 2.05
```

## Sample-point comparison (L4)

The sample-point comparator checks that two adapters produce matching values at shared evaluation points. This is the layer 4 comparison in the pipeline — it catches equivalent-but-different expressions by evaluating them numerically.

```python
from elegua.compare_numeric import make_numeric_comparator

# toler = 1e-6, min_samples = 1
compare = make_numeric_comparator(tol=1e-6, min_samples=1)

token_a = ValidationToken(
    adapter_id="oracle",
    status=TaskStatus.OK,
    result={
        "numeric_samples": [
            {"vars": {"x": 0.0}, "value": 1.0},
            {"vars": {"x": 1.0}, "value": 2.0},
        ]
    },
)
token_b = ValidationToken(
    adapter_id="iut",
    status=TaskStatus.OK,
    result={
        "numeric_samples": [
            {"vars": {"x": 0.0}, "value": 1.000001},
            {"vars": {"x": 1.0}, "value": 2.0},
        ]
    },
)

assert compare(token_a, token_b) == TaskStatus.OK  # within 1e-6 tolerance
```

## Registering the numeric layer in the pipeline

The ``make_numeric_layer`` factory creates a single ``LayerFn`` that routes by payload type. Register it at layer 3 (after L1 identity and L2 structural) with ``exclude_keys=NUMERIC_KEYS`` so that L1/L2 do not compare numeric fields:

```python
from elegua.comparison import ComparisonPipeline
from elegua.numeric.layer import make_numeric_layer, NUMERIC_KEYS
from elegua.numeric.tolerance import MixedTolerance

pipeline = ComparisonPipeline()  # includes L1 + L2
pipeline.register(
    3, "numeric",
    make_numeric_layer(
        strategy=MixedTolerance(atol=1e-6, rtol=1e-3),
        array_strategy=MixedTolerance(atol=1e-6, rtol=1e-3),
        return_diagnostics=True,
    ),
    exclude_keys=NUMERIC_KEYS,
)
```

The layer routes by payload key:
- ``value`` → scalar comparator
- ``values`` → array comparator
- ``numeric_samples`` → sample-point comparator
- No numeric fields → ``MATH_MISMATCH`` (non-opt-in fixtures pass through to L1/L2)

### Profile-based pipeline

For pipelines that need different tolerances per quantity:

```python
from elegua.numeric.tolerance import ToleranceProfile, AbsoluteTolerance, RelativeTolerance

profile = ToleranceProfile()
profile.register("energy", AbsoluteTolerance(atol=1e-8))
profile.register("rate", RelativeTolerance(rtol=1e-3))

pipeline.register(
    3, "numeric",
    make_numeric_layer(profile=profile),
    exclude_keys=NUMERIC_KEYS,
)
```

## Summary

| Need | Use |
|------|-----|
| Simple fixed tolerance | ``AbsoluteTolerance(atol=1e-6)`` |
| Error scales with magnitude | ``RelativeTolerance(rtol=1e-3)`` |
| Both | ``MixedTolerance(atol=1e-6, rtol=1e-3)`` |
| Bit-level precision | ``ULPTolerance(n_ulps=2)`` |
| Noisy / Monte Carlo results | ``StochasticTolerance(k=3.0)`` |
| Different tolerances per quantity | ``ToleranceProfile`` with ``make_numeric_layer(profile=...)`` |
| Array comparison | ``make_array_comparator(tolerance, k=5, return_diagnostics=True)`` |
| Sample-point L4 check | ``make_numeric_comparator(tol=1e-6, min_samples=1)`` |