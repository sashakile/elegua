# Specification: Three-Layer Testing Architecture

## Metadata
- **Change-ID**: `REQ-TEST-001`
- **Version**: `1.5.0`
- **Status**: `PARTIAL`
- **Last Updated**: 2026-03-23

## Purpose
This specification defines the three-layer testing architecture for Eleguá. It ensures that symbolic systems are mathematically correct and performant by providing a language-agnostic framework for validation across multiple tiers.

## Requirements

### Requirement: Functional Validation
The testing architecture SHALL validate the functional equivalence of an implementation against a high-fidelity oracle using a default numerical tolerance of `1e-12`.

#### Scenario: Validate symbolic transformation
- **GIVEN** a symbolic transformation task
- **WHEN** it is executed in an IUT (Tier 2/3)
- **THEN** the result MUST match the Oracle (Tier 1) within `1e-12` relative tolerance.

#### Scenario: Negative - Verification Failure
- **GIVEN** a task where the results diverge beyond `1e-12`
- **WHEN** the comparison is performed
- **THEN** the runner MUST report a `MATH_MISMATCH` and output the delta.

### Requirement: Language-Agnostic Property Specification
The architecture SHALL support property-based tests that describe mathematical laws independent of the specific implementation language.

#### Scenario: Verify identity law
- **GIVEN** a property test defining an identity law
- **WHEN** it is run across multiple adapters
- **THEN** it MUST hold for the specified number of random samples.

### Requirement: Verdict Evaluation
The architecture SHALL evaluate test results against expected outcomes defined in the test file, producing a `Verdict` with status `pass`, `fail`, `skip`, or `error`.

#### Scenario: Expression match
- **GIVEN** a test case with `expected.expr = "x^2"`
- **WHEN** the last operation produces a token with `result.repr = "x^2"`
- **THEN** the verdict MUST be `pass`.

#### Scenario: Expression mismatch
- **GIVEN** a test case with `expected.expr = "x^2"`
- **WHEN** the last operation produces a token with `result.repr = "x^3"`
- **THEN** the verdict MUST be `fail` with actual and expected values in the message.

#### Scenario: Expected error
- **GIVEN** a test case with `expected.expect_error = true`
- **WHEN** the operation raises an operational error
- **THEN** the verdict MUST be `pass`.

#### Scenario: No expected block means pass
- **GIVEN** a test case with no `[tests.expected]` section
- **WHEN** execution completes without error
- **THEN** the verdict MUST be `pass` (execution-only test).

#### Scenario: Normalizer-based comparison
- **GIVEN** a caller-injected normalizer function
- **WHEN** `expected.expr` or `expected.normalized` is checked
- **THEN** both actual and expected values MUST be normalized before comparison.

### Requirement: Performance Regression Tracking
The architecture SHALL track execution time and memory usage, flagging regressions exceeding a defined threshold (default: 1.5x baseline).

#### Scenario: Negative - Performance Regression Detected
- **GIVEN** a new version of an implementation that is significantly slower than the previous version
- **WHEN** the Layer 3 tests are run
- **THEN** the runner MUST exit with code `1` and report a `PERFORMANCE_REGRESSION`.

## Design Details

### 1. Architecture Overview
- **Layer 1**: Unit tests (TOML test files, Oracle validation via `IsolatedRunner`/`MultiTierRunner`).
- **Layer 2**: Property-based tests (TOML property specs, invariant validation via `PropertyRunner`).
- **Layer 3**: Performance tests (CSV reports, Regression tracking) — NOT YET IMPLEMENTED.

### 2. CLI Interface
**Status:** NOT YET IMPLEMENTED. All functionality is available via the Python API.

**Planned command:** `elegua-test run --layer [1|2|3]`

**Planned flags:**
- `--fail-fast`: Stop on first failure.
- `--tolerance <float>`: Override numerical tolerance (default: `1e-12`).
- `--baseline <file>`: CSV file for Layer 3 comparison.

### 3. Test File Format (TOML)

Test files use a structured TOML format parsed by `load_test_file()` (alias: `load_sxact_toml()`). Invalid files raise `SchemaError`.

#### 3.1 Complete Schema

```toml
[meta]
id = "test_file_id"                 # REQUIRED: unique identifier
description = "What this file tests" # REQUIRED: human-readable description
tags = ["algebra", "rubi"]          # optional: for filtering
layer = 1                           # optional: testing layer (default: 1)
oracle_is_axiom = true              # optional: oracle result is ground truth (default: true)
skip = "reason to skip"             # optional: skip entire file

# --- File-level setup (optional) ---
# Operations run once; store_as bindings are available to ALL tests.

[[setup]]
action = "LoadPackage"
[setup.args]
name = "xAct"

[[setup]]
action = "DefManifold"
store_as = "manifold"               # optional: store result.repr under this name
[setup.args]
name = "M"
dim = 4

# --- Test cases ---

[[tests]]
id = "test_case_id"                 # REQUIRED: unique within file
description = "What this test does"  # REQUIRED
tags = ["involution"]               # optional
dependencies = ["other_test_id"]    # optional: prerequisite test IDs
skip = "reason"                     # optional: skip this test
oracle_is_axiom = true              # optional: override file-level default

[[tests.operations]]
action = "Integrate"                # REQUIRED: operation name
store_as = "antideriv"              # optional: bind result.repr to name
[tests.operations.args]             # domain-specific arguments
expression = "x^2"
variable = "x"

[[tests.operations]]
action = "Differentiate"
store_as = "result"
[tests.operations.args]
expression = "$antideriv"           # $-references resolve from bindings
variable = "x"

[tests.expected]                    # optional: omit for execution-only tests
expr = "x^2"                       # string match against result.repr
normalized = "x^2"                  # match after normalizer applied
value = 42                          # match against result.repr as string
is_zero = true                      # check if normalized repr equals "0"
comparison_tier = 2                 # which tier to compare against
expect_error = true                 # pass if operation raises an error
[tests.expected.properties]         # match against result.properties dict
symmetric = true
rank = 2
```

#### 3.2 Data Models

| Model | Fields | Notes |
|-------|--------|-------|
| `TestFileMeta` | `id`, `description`, `tags`, `layer`, `oracle_is_axiom`, `skip` | File-level metadata |
| `Operation` | `action` (required), `args`, `store_as` | `store_as` must match `[a-zA-Z_]\w*` |
| `Expected` | `expr`, `normalized`, `value`, `is_zero`, `properties`, `comparison_tier`, `expect_error` | All fields optional |
| `TestCase` | `id`, `description` (required), `operations` (≥1 required), `expected`, `tags`, `dependencies`, `skip`, `oracle_is_axiom` | |
| `TestFile` | `meta`, `setup`, `tests` | Top-level container |

#### 3.3 Flattening to `EleguaTask`

`TestFile.to_tasks()` flattens the hierarchical structure into a flat `list[EleguaTask]` — setup operations first, then test operations in order. If an operation has `store_as`, it is included in the payload as `_store_as`.

#### 3.4 Layer 3: Performance Report (CSV) — planned
`task_id, duration_ms, memory_mb, tier, timestamp`

### 4. Verdict Evaluation

The verdict system (`evaluate_expected()`) compares a `TestRunResult` against the `TestCase.expected` block. It returns a `Verdict(status, actual, expected, message)` where status is one of `pass`, `fail`, `skip`, `error`.

**Evaluation order** (short-circuits on first failure):
1. **Skip**: If `result.skipped` → `skip`.
2. **No expected**: If `expected` is `None` → `pass` (execution-only test).
3. **expect_error**: If `expected.expect_error` is true, pass when result has an error, fail otherwise.
4. **Error propagation**: If result has an error (and no `expect_error`) → `error`.
5. **expr check**: Compare `result.repr` against `expected.expr` (with `$ref` substitution and optional normalizer).
6. **normalized check**: Compare `normalizer(result.repr)` against `expected.normalized`.
7. **is_zero check**: Check if `normalizer(result.repr) == normalizer("0")`.
8. **value check**: Compare `str(expected.value)` against `result.repr`.
9. **properties check**: For each key in `expected.properties`, compare against `result.properties[key]`.
10. All checks pass → `pass`.

**Domain injection**: The caller supplies an optional `normalizer: Callable[[str], str]` for semantic comparison (e.g., tensor expression canonicalization). Without a normalizer, string equality is used.

**`$ref` substitution in expected.expr**: The `expected.expr` field supports `$name` references, resolved from the test's accumulated bindings. This enables patterns like asserting `$antideriv` equals the original expression after round-trip verification.

### 5. EchoOracle (Test Utility)

`EchoOracle` is a lightweight stdlib HTTP server (no Flask) for integration testing. It implements the full oracle protocol by echoing back the `expr` field as the result.

```python
from elegua.testing import EchoOracle
from elegua.oracle import OracleClient

with EchoOracle(port=0) as oracle:
    client = OracleClient(oracle.url)
    assert client.health()
```

**Endpoints**: `/health` → `{"status": "ok"}`, `/evaluate` and `/evaluate-with-init` → `{"status": "ok", "result": <expr>, "timing_ms": 1}`, `/cleanup` → `{"status": "ok"}`, `/restart` → `{"status": "ok"}`, `/check-state` → `{"clean": true, "leaked": []}`.

**Design**: Runs in a background daemon thread. Uses `allow_reuse_address` and ephemeral port (`port=0`) for test isolation. Suppresses request logging. Context manager ensures clean shutdown.

### 6. Implementation Status
- **Layer 1 (Unit tests)**: IMPLEMENTED. TOML-based test definitions via `load_test_file()`, `IsolatedRunner`, `MultiTierRunner`, verdict evaluation.
- **Layer 2 (Property tests)**: IMPLEMENTED. `PropertyRunner` with PCG64 seeds, `GeneratorRegistry`, TOML spec format. Python API only (no CLI yet). See `specs/property-testing/spec.md`.
- **Layer 3 (Performance tests)**: NOT YET IMPLEMENTED. CSV reporting and regression tracking remain future work.
- **CLI (`elegua-test`)**: NOT YET IMPLEMENTED. All functionality is available via Python API.

### 7. Non-Goals
- Real-time profiling (Layer 3 is for coarse-grained regression only).
- Direct code modification or automated fixing.

### 8. Remaining Work
- [ ] Implement `elegua-test` CLI wrapper.
- [ ] Create `perf_tracker.py` for Layer 3 telemetry.
