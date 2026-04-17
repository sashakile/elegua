# Comparison pipeline

**The comparison pipeline cascades through up to 4 layers so you can confirm mathematical equivalence at the cheapest level possible.**

The pipeline determines whether two `ValidationToken` results are mathematically equivalent, stopping at the first layer that confirms a match.

**Prerequisite:** you need two `ValidationToken` objects — one from the Oracle adapter and one from the IUT adapter. See [Writing an adapter](adapters.md) for how to produce them, or [Task lifecycle](tasks.md) for the data model.

## Compare two validation tokens

```python
from elegua.comparison import ComparisonPipeline

pipeline = ComparisonPipeline()
result = pipeline.compare(oracle_token, iut_token)
print(result.status)      # TaskStatus.OK or TaskStatus.MATH_MISMATCH
print(result.layer)       # which layer resolved the comparison (1-4)
print(result.layer_name)  # human-readable name (e.g. "identity", "structural")
```

## Layer 1 — Identity

Structural equality of the `result` dicts.

```python
from elegua.comparison import compare_identity

status = compare_identity(token_a, token_b)  # OK or MATH_MISMATCH
```

This is the fastest check. If both adapters produce structurally identical output, no further analysis is needed.

## Layer 2 — Structural

AST isomorphism via sorted canonical form. Handles differences in dict key ordering and commutative argument reordering.

```python
from elegua.comparison import compare_structural

# These are structurally equivalent:
# {"fn": "Add", "args": [1, 2]}  vs  {"fn": "Add", "args": [2, 1]}
status = compare_structural(token_a, token_b)
```

!!! note
    Layer 2 sorts all list items, which treats every operation as commutative. Non-commutative operations (like subtraction) may produce false positives. Register domain-specific normalizers in Layers 3-4 to handle these cases.

## Register semantic and invariant layers

**Layer 3 (Canonical)** uses pluggable normalizer rules for semantic equivalence. **Layer 4 (Invariant)** uses pluggable invariant checks such as numeric sample comparison. Both are domain-specific — register them via `ComparisonPipeline.register()`.

```python
from elegua.comparison import ComparisonPipeline
from elegua.models import ValidationToken
from elegua.task import TaskStatus

def compare_canonical(token_a: ValidationToken, token_b: ValidationToken) -> TaskStatus:
    """Layer 3: normalize expressions before comparing."""
    norm_a = normalize(token_a.result)  # your domain-specific normalizer
    norm_b = normalize(token_b.result)
    return TaskStatus.OK if norm_a == norm_b else TaskStatus.MATH_MISMATCH

def compare_numeric(token_a: ValidationToken, token_b: ValidationToken) -> TaskStatus:
    """Layer 4: sample numeric values and check approximate equality."""
    samples_a = evaluate_numerically(token_a.result)
    samples_b = evaluate_numerically(token_b.result)
    return TaskStatus.OK if all_close(samples_a, samples_b) else TaskStatus.MATH_MISMATCH

pipeline = ComparisonPipeline()  # includes L1 + L2 by default
pipeline.register(3, "canonical", compare_canonical)
pipeline.register(4, "numeric", compare_numeric)

result = pipeline.compare(oracle_token, iut_token)
```

Use the `exclude_keys` parameter to strip keys from token results before lower layers run. For example, if your L4 layer adds a `"timing"` key that should not affect L1/L2 equality:

```python
pipeline.register(4, "numeric", compare_numeric, exclude_keys=frozenset({"timing"}))
```

Property-based testing is a separate Hypothesis-based tool that can complement pipeline work; see [Property testing](property-testing.md).

## Whole game: L3 normalizer end-to-end

This self-contained example defines a canonical normalizer for commutative addition, registers it as Layer 3, and compares two tokens that differ structurally but are semantically equal.

```python
from elegua.adapter import WolframAdapter
from elegua.comparison import ComparisonPipeline
from elegua.models import ValidationToken
from elegua.task import EleguaTask, TaskStatus

# Two representations of "x + y":
#   Oracle returns {"fn": "Plus", "args": ["x", "y"]}
#   IUT    returns {"fn": "Plus", "args": ["y", "x"]}
oracle_token = ValidationToken(
    adapter_id="oracle",
    status=TaskStatus.OK,
    result={"fn": "Plus", "args": ["x", "y"]},
)
iut_token = ValidationToken(
    adapter_id="iut",
    status=TaskStatus.OK,
    result={"fn": "Plus", "args": ["y", "x"]},
)

# L1 (identity) fails: dicts are not equal.
# L2 (structural) succeeds here because it sorts all lists,
# but for non-commutative ops you'd need a domain-aware L3.

def sort_commutative_args(
    token_a: ValidationToken, token_b: ValidationToken
) -> TaskStatus:
    """L3: sort args for known commutative functions, then compare."""
    commutative = {"Plus", "Times"}
    def normalize(result: dict) -> dict:
        if result.get("fn") in commutative:
            return {**result, "args": sorted(result["args"], key=repr)}
        return result
    return (
        TaskStatus.OK
        if normalize(token_a.result) == normalize(token_b.result)
        else TaskStatus.MATH_MISMATCH
    )

pipeline = ComparisonPipeline()
pipeline.register(3, "commutative-canonical", sort_commutative_args)

result = pipeline.compare(oracle_token, iut_token)
print(f"Layer {result.layer} ({result.layer_name}): {result.status.value}")
# => Layer 2 (structural): ok
#    (L2 already catches this case; L3 would catch subtler rewrites)
```

## Read the comparison result

The pipeline returns a `ComparisonResult` dataclass:

```python
from elegua.comparison import ComparisonResult

# result.status     — TaskStatus.OK or TaskStatus.MATH_MISMATCH
# result.layer      — the layer number that produced the verdict (1-4)
# result.layer_name — human-readable name (e.g. "identity", "structural")
```

## L4 numeric comparison vs property-based testing

PCG64 cross-platform deterministic sampling is used for L4 numeric comparison (`compare_numeric.py`), not for property-based testing. These are separate concerns: Hypothesis owns property-test randomness and shrinking, while the L4 comparator owns cross-CAS sample-point agreement inside `ComparisonPipeline`. See [Property testing](property-testing.md) for the Hypothesis-based workflow.
