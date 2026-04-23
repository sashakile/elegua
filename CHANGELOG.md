# Changelog

All notable changes to Eleguá are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-03-19

Initial release of the Eleguá multi-tier test harness.

### Added

- **Orchestrator core** — `EleguaTask` state machine with validated transitions
  (`PENDING → RUNNING → OK | MATH_MISMATCH | EXECUTION_ERROR | TIMEOUT`),
  `ActionPayload` and `ValidationToken` interchange models.
- **4-layer comparison pipeline** — cascading equivalence checks: identity (L1),
  structural via sorted canonical form (L2), canonical normalizer rules (L3),
  and invariant/numeric comparison (L4). `ComparisonPipeline` supports pluggable
  layer registration.
- **Property-based testing** — Hypothesis-based `PropertyRunner` with automatic
  shrinking, TOML property specs, and `StrategyRegistry` for domain-specific
  strategies. *(Note: earlier PCG64-seeded approach is now part of L4 comparison, not property testing).*
- **Adapter lifecycle** — `Adapter` ABC with `initialize()`/`teardown()` hooks,
  context manager support, and teardown-exception suppression.
  `WolframAdapter` stub for tracer-bullet validation.
- **WolframOracleAdapter** — HTTP client for real Wolfram kernel oracle,
  decoupled from xAct action vocabulary.
- **IsolatedRunner** — per-file adapter lifecycle with per-test binding scope.
- **MultiTierRunner** — Oracle vs IUT cross-comparison with verdict reporting.
- **ExecutionContext** — `store_as` variable chaining across tasks within a file.
- **sxAct bridge** — TOML format bridge loader for sxAct test definitions.
- **Snapshot record/replay** — capture oracle responses for offline CI runs.
- **SHA-256 blob store** — content-addressed storage for payloads exceeding 1 MB,
  with transparent `maybe_store()`/`maybe_resolve()` handling.
- **Verdict logic** — `evaluate_expected` for asserting test outcomes against
  expected results.
- **Domain exception hierarchy** — `EleguaError`, `SchemaError`, `AdapterError`,
  `OracleError` with operation context and exception chaining.
- **TOML test format** — declarative test definitions with `[meta]` and
  `[[tasks]]` sections, validated by `load_toml_tasks()`.
- **Documentation** — mkdocs Material site with architecture overview,
  getting-started tutorial, user guide (tasks, adapters, comparison,
  property testing, blob store, TOML format), and auto-generated API reference.
- **Developer tooling** — `justfile` with `setup`, `check`, `fix`, `test`, `cov`,
  `ci` commands; pre-commit hooks (ruff, pyright, typos, vale); pre-push hook
  (pytest); GitHub Actions CI across Python 3.11–3.13.
- **336 tests** with 100% line coverage.

[0.1.0]: https://github.com/sashakile/elegua/releases/tag/v0.1.0
