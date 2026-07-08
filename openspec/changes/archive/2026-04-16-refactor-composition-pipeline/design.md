## Context

Eleguá has two comparison/evaluation systems that evolved independently:
- **ComparisonPipeline** (`comparison.py`): multi-layer token comparison producing `ComparisonResult(status: TaskStatus, layer: int)`. Used by `MultiTierRunner`.
- **Verdict evaluation** (`verdict.py`): single-tier expected-value checking producing `Verdict(status: Literal["pass","fail","skip","error"])`. Used by test consumers.

These systems have no shared outcome type. A test can pass multi-tier comparison but has no unified verdict, and vice versa. Additionally, L1/L2 comparison hardcodes knowledge of L4 key names, creating implicit coupling between layers.

## Goals / Non-Goals

- **Goals:**
  - Bridge `ComparisonResult` and `Verdict` via a mapping method (not type unification)
  - Make layer key exclusion declarative and per-layer
  - Make `OracleAdapter` result mapping injectable
  - Deprecate the dead-end `runner.py` path
- **Non-Goals:**
  - Merging `TaskStatus` and `Verdict.status` into a single enum (they serve different domains)
  - Removing `runner.py` (deprecation only; removal is a future change)
  - Refactoring `ExecutionContext` monadic patterns (low impact, deferred)

## Decisions

### 1. Verdict.from_comparison() bridge method

**Decision:** Add a `@classmethod` on `Verdict` that maps `ComparisonResult` → `Verdict`.

Mapping:
- `TaskStatus.OK` → `Verdict(status="pass")`
- `TaskStatus.MATH_MISMATCH` → `Verdict(status="fail", message=f"Mismatch at layer {r.layer}")`
- `TaskStatus.EXECUTION_ERROR` → `Verdict(status="error")`
- `TaskStatus.TIMEOUT` → `Verdict(status="error", message="Timeout")`
- Any other `TaskStatus` → `Verdict(status="error", message=f"Unknown comparison status: {status}")`

**Note:** In practice, `ComparisonPipeline.compare()` only produces `OK` or `MATH_MISMATCH`. The `EXECUTION_ERROR` and `TIMEOUT` mappings exist defensively for callers who construct `ComparisonResult` directly (e.g., `MultiTierRunner._compare_test`). A future enhancement may accept `VerificationResult` to include oracle/IUT error messages.

**Alternatives considered:**
- Shared outcome enum → rejected: couples two distinct domains (task state machine vs test verdict)
- Adapter pattern wrapping ComparisonResult → rejected: adds a third type instead of bridging

### 2. Declarative layer key exclusion

**Decision:** Add `exclude_keys: frozenset[str] = frozenset()` to `_RegisteredLayer`. Change `ComparisonPipeline.register()` signature to accept optional `exclude_keys`. Before running layer N, the pipeline collects `exclude_keys` from all layers with `num > N`, unions them, and strips those keys from both token results before passing them to layer N's function. The declaring layer itself always sees unstripped data (it needs its own keys).

**Concrete example:** Given layers 1 (identity), 2 (structural), 3 (canonical, `exclude_keys={"canonical_form"}`), 4 (numeric, `exclude_keys={"numeric_samples"}`):
- Layer 1 sees tokens with `canonical_form` and `numeric_samples` stripped (union of L3 + L4 exclusions)
- Layer 2 sees tokens with `canonical_form` and `numeric_samples` stripped (same)
- Layer 3 sees tokens with `numeric_samples` stripped (only L4 exclusion; L3 sees its own keys)
- Layer 4 sees unstripped tokens (no layer has `num > 4`)

**Why not per-layer strip functions?** A frozenset is simpler, cheaper, and sufficient. Full strip functions would be needed only if exclusion logic were non-trivial (e.g., conditional).

**Migration:** Current L4 registration `pipeline.register(4, "numeric", fn)` becomes `pipeline.register(4, "numeric", fn, exclude_keys=frozenset({"numeric_samples"}))`. The default `ComparisonPipeline()`  (L1+L2 only) is unchanged — no exclusion keys, no stripping. The caller who adds L4 is responsible for passing `exclude_keys`.

### 3. Injectable result mapper

**Decision:** Add `result_mapper: Callable[[str, dict[str, Any], dict[str, Any]], ValidationToken] | None` to `OracleAdapter.__init__()`. When `None`, falls back to the existing `_map_result()`. This mirrors the `expr_builder` injection pattern already established.

### 4. runner.py deprecation

**Decision:** Add `DeprecationWarning` to `load_toml_tasks()` and `run_tasks()` pointing to `load_test_file()` + `IsolatedRunner`. Keep exports in `__init__.py` for backward compatibility.

## Risks / Trade-offs

- **`from_comparison()` creates a soft dependency** between verdict and comparison modules → Mitigated: it's a classmethod that imports nothing new; the mapping is trivial.
- **Changing `register()` signature** → Mitigated: `exclude_keys` has a default value; existing callers are unaffected.
- **Deprecation of `runner.py`** may affect external users → Mitigated: `runner.py` is not documented in external docs; it's an internal convenience.

## Open Questions

None remaining — the `VerificationResult` bridge question is addressed in Decision 1 as a documented future enhancement.
