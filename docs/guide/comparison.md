# Comparison pipeline

The comparison pipeline determines whether two `ValidationToken` results are mathematically equivalent. It cascades through up to 4 layers, stopping at the first that confirms a match.

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

**Layer 3 (Canonical)** uses pluggable normalizer rules for semantic equivalence. **Layer 4 (Invariant)** uses pluggable invariant checks such as numeric sample comparison. Both are domain-specific — register them on a `ComparisonPipeline` instance. Property-based testing is a separate Hypothesis-based tool that can complement pipeline work; see [Property testing](property-testing.md).

## Read the comparison result

The pipeline returns a `ComparisonResult` dataclass:

```python
from elegua.comparison import ComparisonResult

# result.status     — TaskStatus.OK or TaskStatus.MATH_MISMATCH
# result.layer      — the layer number that produced the verdict (1-4)
# result.layer_name — human-readable name (e.g. "identity", "structural")
```
