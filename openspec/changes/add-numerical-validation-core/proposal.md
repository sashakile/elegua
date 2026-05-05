# Change: Add numerical validation core capabilities

## Why
Eleguá's current comparison pipeline and fixture model are strong for symbolic cross-implementation checks, but numerical-validation users must reimplement common primitives such as tolerances, adapter capability gating, differential checks, convergence tracking, provenance, array diagnostics, and warm adapter lifecycles. Adding these as domain-agnostic core capabilities makes Eleguá useful for finance, physics, ML, scientific-computing ports, and other numerical oracle workflows without embedding finance-specific logic in core.

## What Changes
- Add a built-in numeric comparison layer with composable tolerance strategies, numeric payload metadata, array diagnostics, and versioned tolerance profiles.
- Add adapter capability declarations and fixture-side capability negotiation with explicit skip reporting.
- Add first-class differential and convergence fixture types so relation checks and empirical error-rate checks use the same reporting/provenance/comparison infrastructure as ordinary fixtures.
- Add provenance capture and a longitudinal history store with local and CI backends plus `elegua history` queries.
- Extend the blob store for typed numerical arrays, manifests, lazy fetch, and top-K disagreement reporting.
- Add parallel adapter dispatch, adapter lifecycle metadata, bounded connection pooling, reset/close semantics, and an isolation verification helper.
- Add structural fixture improvements: matrix expansion, inheritance/composition, tag/capability/adapter selection, full-pipeline diagnostic mode, disagreement minimization, and fixture coverage reports.
- Keep finance-specific profiles, Greek conventions, MC finance noise models, calibration round-trips, arbitrage relations, and calendar corpora out of core; those belong in a future `elegua-finance` plugin change.

## Impact
- Affected specs: `numerical-validation` (new domain-agnostic capability), with implementation touching existing orchestrator, comparison, fixture loading, blob store, adapter lifecycle, reporting, and CLI surfaces.
- Affected code: comparison pipeline, `ValidationToken` metadata conventions, adapter base class, fixture/TOML loaders, runners, blob store, report/verdict models, CLI entry points, docs, and tests.
- Backwards compatibility: existing symbolic fixtures and adapters remain valid; all new fixture types, layers, metadata, and CLI flags are additive. Existing comparison short-circuit behavior remains the default unless diagnostic mode is requested.
