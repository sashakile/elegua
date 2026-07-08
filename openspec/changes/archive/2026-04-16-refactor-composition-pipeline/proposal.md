# Change: Improve pipeline composability and eliminate type-flow friction

## Why

A composability analysis identified six friction points where Eleguá's internal type flows break, duplicate, or couple in ways that hinder extension. The two most impactful are: (1) two parallel, disconnected comparison systems (`ComparisonResult` vs `Verdict`) with no shared outcome algebra, and (2) L1/L2 layers hardcoding knowledge of L4-only keys (`_L4_KEYS`), violating layer independence. Fixing these unlocks cleaner extension of both the comparison pipeline and the verdict system, and aligns with the project convention of "extension over modification."

## What Changes

1. **Unify outcome types** — Introduce a shared outcome mapping so `Verdict` and `ComparisonResult` can interoperate. `Verdict.status` stays as `Literal["pass","fail","skip","error"]` but gains a `from_comparison()` class method that maps `ComparisonResult` → `Verdict`. This bridges the two systems without merging their type hierarchies.

2. **Layer key exclusion** — Replace the hardcoded `_L4_KEYS` frozenset with per-layer declared exclusion sets. Each `_RegisteredLayer` gains an optional `exclude_keys: frozenset[str]` field. The pipeline collects exclusions from *higher-numbered* layers and strips them before running each layer. L1/L2 no longer reference `_L4_KEYS` directly.

3. **Injectable result mapper for `OracleAdapter`** — Add an optional `result_mapper` parameter to `OracleAdapter.__init__()`, mirroring the existing `expr_builder` pattern. The default mapper preserves current behavior (Assert handling, status mapping). Custom mappers enable domain-specific result translation without subclassing.

4. **Deprecate `runner.py`** — Mark `load_toml_tasks()` and `run_tasks()` as deprecated. They are a subset of the bridge → `IsolatedRunner` path and cannot participate in comparison or verdict evaluation. Add deprecation warnings pointing to `load_test_file()` + `IsolatedRunner`.

## Deferred

Two lower-priority composability findings are intentionally deferred:

- **Monadic context leakage** (`isolation.py`, `context.py`): Manual `Optional` unwrapping in `_execute_op` and `resolve_refs`. Low extension impact; not worth the abstraction cost today.
- **Non-endomorphic adapter execute**: `Adapter.execute(EleguaTask) → ValidationToken` diverges input/output types by design (different domains). No action needed.

## Impact

- Affected specs: `orchestrator-core`, `testing-architecture`
- Affected code: `comparison.py`, `verdict.py`, `wolfram/adapter.py`, `runner.py`
- Synergy: The injectable `result_mapper` and declarative layer exclusion directly enable the in-progress `add-sympy-adapter` change.
- **No breaking changes** — all changes are additive or internal. Deprecations emit warnings; no existing API is removed.
