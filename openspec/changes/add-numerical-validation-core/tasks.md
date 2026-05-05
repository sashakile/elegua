## 1. Numeric comparison layer
- [ ] 1.1 Add failing tests for scalar absolute, relative, mixed, ULP, stochastic, and profile tolerance comparisons.
- [ ] 1.2 Add failing tests for vector/array elementwise comparisons, max disagreement, argmax disagreement, and failing counts.
- [ ] 1.3 Implement numeric payload helpers, tolerance strategy classes, profile registry, and conservative `numerical_default` profile.
- [ ] 1.4 Register the numeric comparison layer as an opt-in built-in layer after canonical comparison and before invariant comparison.
- [ ] 1.5 Document scalar, vector, and stochastic examples.

## 2. Adapter capabilities and negotiation
- [ ] 2.1 Add failing tests for adapter capability declarations, fixture `requires`/`prefers` parsing, and incompatible adapter skips.
- [ ] 2.2 Implement capability data model, standard vocabulary, and fixture validation.
- [ ] 2.3 Implement negotiation across tiers, tier overrides, skip verdicts, skip reasons, and `--capability` filtering.
- [ ] 2.4 Document standard capabilities and examples for shipped adapters.

## 3. Differential fixtures
- [ ] 3.1 Add failing loader tests for two-evaluation, multi-evaluation, and cross-adapter differential fixtures.
- [ ] 3.2 Add failing relation-plugin tests for `equality`, `linear_combination`, `numerical_derivative`, and `convergence_residual`.
- [ ] 3.3 Implement `DifferentialFixture`, evaluation routing, relation plugin registry, and synthetic residual tokens.
- [ ] 3.4 Add an executable AD-vs-FD documentation example.

## 4. Convergence fixtures
- [ ] 4.1 Add failing tests for refinement execution, reference modes, fitted rate, R², and failed diagnostics.
- [ ] 4.2 Implement `ConvergenceFixture`, log-space fitting, adapter/analytic/literal/Richardson references, replications, and CRN handling.
- [ ] 4.3 Add examples for MC, midpoint/trapezoidal, and deterministic quadrature convergence.

## 5. Provenance and history
- [ ] 5.1 Add failing tests for automatic provenance fields on tokens and verdicts.
- [ ] 5.2 Implement schema-versioned SQLite and DuckDB/Parquet-compatible history writers behind a common interface.
- [ ] 5.3 Implement `elegua history fixture`, `regression`, `ranking`, and `flaky` queries.
- [ ] 5.4 Document local and CI storage/retention policies.

## 6. Numerical array blob support
- [ ] 6.1 Add failing tests for NPY array blob manifests, checksums, lazy manifest reads, and round-trip retrieval.
- [ ] 6.2 Implement `put_array` / `get_array` with NPY backend and optional Zarr support.
- [ ] 6.3 Integrate top-K array disagreement reports with the numeric layer.

## 7. Parallel execution and pooling
- [ ] 7.1 Add failing tests for parallel cross-adapter dispatch, partial failure reporting, and bounded pool behavior.
- [ ] 7.2 Implement adapter lifecycle declarations, `reset()`, `close()`, connection pools, and runner parallelism controls.
- [ ] 7.3 Add `verify_isolation` helper and worked example for a stateful adapter.

## 8. Structural fixture and CLI improvements
- [ ] 8.1 Add failing tests for matrix expansion, naming, tag propagation, and fixture inheritance cycle detection.
- [ ] 8.2 Implement matrix expansion and inheritance/composition resolution at load time.
- [ ] 8.3 Add CLI filters for tag, capability, adapter, changed fixtures, and last-run failures.
- [ ] 8.4 Add `--full-pipeline` diagnostic mode and concordance reporting.
- [ ] 8.5 Add disagreement minimization using Hypothesis shrinking.
- [ ] 8.6 Add fixture coverage reports with configurable axes and CSV/Markdown output.

## 9. Quality gates and release documentation
- [ ] 9.1 Maintain backwards compatibility tests for existing symbolic fixtures and adapters.
- [ ] 9.2 Ensure new modules meet project coverage targets and include property tests for tolerance symmetry/reflexivity.
- [ ] 9.3 Update guide docs, API docs, examples, and changelog migration notes.
- [ ] 9.4 Record follow-up proposal(s) for `elegua-finance` plugin work without implementing finance-specific logic in this change.
