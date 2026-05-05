## ADDED Requirements
### Requirement: Numeric Comparison Layer
Eleguá SHALL provide an opt-in numeric comparison layer that compares numerical validation tokens using composable tolerance strategies after canonical comparison and before domain-specific invariant comparison.

#### Scenario: Mixed tolerance scalar comparison passes
- **GIVEN** two successful validation tokens tagged with numeric scalar payloads and a fixture comparison strategy `mixed` with `atol = 1e-8` and `rtol = 1e-6`
- **WHEN** the absolute difference is less than or equal to `atol + rtol * max(abs(a), abs(b))`
- **THEN** the numeric layer MUST return a passing verdict.

#### Scenario: Stochastic comparison uses standard error
- **GIVEN** one or both numeric payloads include `standard_error`
- **WHEN** the fixture uses stochastic tolerance with multiplier `k`
- **THEN** the numeric layer MUST compare the value difference against `k * sqrt(se_a^2 + se_b^2)`, treating a missing standard error as exact.

#### Scenario: Array comparison reports disagreement summary
- **GIVEN** two numeric array payloads with matching shapes
- **WHEN** one or more elements fail the configured tolerance
- **THEN** the verdict MUST include maximum disagreement, argmax location, failing count, and top-K disagreement diagnostics without dumping the full arrays.

### Requirement: Versioned Tolerance Profiles
Eleguá SHALL provide a tolerance profile registry for named, versioned bundles of per-quantity numerical tolerances.

#### Scenario: Fixture resolves tolerance by quantity label
- **GIVEN** a registered tolerance profile containing a tolerance for `quantity_label = "price"`
- **WHEN** a fixture selects that profile and the compared tokens are labelled `price`
- **THEN** Eleguá MUST apply the profile's configured strategy and parameters for `price`.

#### Scenario: Missing profile entry fails clearly
- **GIVEN** a fixture selects a profile and a numeric token has no matching quantity label in that profile
- **WHEN** the numeric layer attempts comparison
- **THEN** it MUST return an error verdict with a structured reason identifying the missing profile entry.

### Requirement: Adapter Capability Negotiation
Adapters SHALL declare capabilities and optional capability metadata so fixtures can require, prefer, or filter compatible adapters before execution.

#### Scenario: Fixture skips incompatible adapter
- **GIVEN** a fixture requiring capabilities `gradient` and `deterministic`
- **WHEN** an adapter lacks `gradient`
- **THEN** the runner MUST skip that adapter for the fixture and report verdict `SKIPPED` with the missing capability in the reason.

#### Scenario: Tier override relaxes a requirement
- **GIVEN** a multi-tier fixture requiring `seedable` except for the oracle tier
- **WHEN** the oracle lacks `seedable` but the IUT adapters provide it
- **THEN** capability negotiation MUST allow the oracle and run the fixture for compatible IUT adapters.

### Requirement: Differential Fixtures
Eleguá SHALL support differential fixtures that evaluate multiple related tasks and validate a relation over their results through registered relation plugins.

#### Scenario: Linear relation produces residual token
- **GIVEN** a differential fixture with named evaluations `primary` and `secondary` and relation plugin `linear_combination`
- **WHEN** both evaluations complete successfully
- **THEN** the relation plugin MUST produce a synthetic validation token representing the residual for normal comparison and reporting.

#### Scenario: Cross-adapter differential routing
- **GIVEN** a differential fixture whose evaluations name specific adapters
- **WHEN** the runner executes the fixture
- **THEN** each evaluation MUST be dispatched to its requested adapter and the relation plugin MUST receive all named tokens.

### Requirement: Convergence Fixtures
Eleguá SHALL support convergence fixtures that run a parameterized task over refinement levels, estimate empirical error-rate behavior, and assert that the fitted rate satisfies configured expectations.

#### Scenario: Convergence rate passes
- **GIVEN** a convergence fixture with levels, a reference mode, expected rate, rate tolerance, and minimum R²
- **WHEN** the fitted log-space convergence rate is within tolerance and R² is at least the configured minimum
- **THEN** the fixture MUST pass and report the fitted rate, fitted constant, R², and per-level errors.

#### Scenario: No external reference uses Richardson
- **GIVEN** a convergence fixture configured with `reference = "richardson"`
- **WHEN** no external analytical adapter or literal truth is supplied
- **THEN** Eleguá MUST estimate the reference from the finest refinement levels and use it for rate fitting.

### Requirement: Provenance and Longitudinal History
Eleguá SHALL attach provenance to evaluations and comparisons and persist run history to a queryable local or CI store.

#### Scenario: Evaluation records provenance
- **GIVEN** a fixture evaluation completes
- **WHEN** its validation token is recorded
- **THEN** provenance MUST include fixture id, fixture content hash, adapter id/version, Eleguá version, timestamp, optional git SHA, environment hash, optional seed, duration, and host.

#### Scenario: History query finds flaky fixtures
- **GIVEN** a history store with repeated verdicts for the same fixture
- **WHEN** the user runs a flaky-history query with a verdict-variance threshold
- **THEN** Eleguá MUST report fixtures whose historical verdict variance exceeds that threshold.

### Requirement: Numerical Array Blob Storage
The blob store SHALL support typed numerical array blobs with manifests, checksums, lazy metadata reads, and array-specific disagreement diagnostics.

#### Scenario: Store and retrieve array blob
- **GIVEN** a numerical array payload exceeding the blob threshold
- **WHEN** the blob store stores it via the array API
- **THEN** it MUST persist a manifest containing schema version, kind, dtype, shape, compression flag, and SHA-256 checksum and MUST retrieve the original array losslessly.

#### Scenario: Lazy manifest validation avoids payload fetch
- **GIVEN** a CI check only needs to validate blob identity and metadata
- **WHEN** lazy-fetch mode is enabled
- **THEN** the blob store MUST validate the manifest and checksum metadata without loading the full array payload unless comparison requires it.

### Requirement: Parallel Execution and Adapter Pooling
Eleguá SHALL execute independent adapter evaluations in parallel up to configured limits and SHALL support opt-in adapter connection pooling with explicit reset semantics.

#### Scenario: Parallel adapter execution preserves partial results
- **GIVEN** a fixture targets multiple adapters and runner parallelism is greater than one
- **WHEN** one adapter fails while another succeeds
- **THEN** the runner MUST wait for all launched adapters and report both the failure and the successful partial result.

#### Scenario: Pooled adapter resets between tasks
- **GIVEN** an expensive adapter declares a soft reset lifecycle and a bounded pool size
- **WHEN** the runner reuses that adapter across tasks
- **THEN** it MUST call `reset()` between tasks and `close()` when the pool shuts down.

### Requirement: Fixture Matrix Expansion and Composition
Fixture loading SHALL support matrix expansion and inheritance/composition so compact fixture definitions can produce independently addressable concrete fixtures.

#### Scenario: Matrix fixture expands cartesian product
- **GIVEN** a matrix fixture with three dimensions containing 5, 3, and 2 values
- **WHEN** the fixture file is loaded
- **THEN** Eleguá MUST produce 30 concrete fixture instances with stable templated names and propagated tags.

#### Scenario: Inheritance cycle is rejected
- **GIVEN** two or more fixtures whose `extends` declarations form a cycle
- **WHEN** the loader resolves inheritance
- **THEN** it MUST reject the file with a schema error identifying the cycle.

### Requirement: Numerical Test Selection and Diagnostics
Eleguá SHALL provide CLI and reporting support for selecting numerical fixtures and diagnosing disagreements across the full comparison pipeline.

#### Scenario: Compose tag, capability, and adapter filters
- **GIVEN** a user selects fixtures with tag, capability, and adapter filters
- **WHEN** the runner builds the execution set
- **THEN** only fixtures satisfying all filters and compatible adapter requirements MUST run.

#### Scenario: Full pipeline diagnostic mode reports concordance
- **GIVEN** diagnostic mode is enabled
- **WHEN** an earlier comparison layer passes
- **THEN** Eleguá MUST continue evaluating later layers and report pass/fail concordance for every configured layer without changing the default short-circuit mode.

### Requirement: Disagreement Minimization and Coverage Reporting
Eleguá SHALL help users reduce numerical failures and identify fixture coverage gaps.

#### Scenario: Minimize disagreeing matrix input
- **GIVEN** a parameterized fixture where at least one expanded input disagrees across adapters
- **WHEN** the user runs disagreement minimization
- **THEN** Eleguá MUST use shrinking to report a minimal disagreeing input and the corresponding adapters.

#### Scenario: Coverage report highlights empty cells
- **GIVEN** fixtures with metadata axes such as adapter, action, method, or regime
- **WHEN** the user requests a coverage report by selected axes
- **THEN** Eleguá MUST output fixture counts and identify zero-coverage cells in machine-readable and human-readable formats.
