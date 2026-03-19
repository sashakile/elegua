# Specification: Three-Layer Testing Architecture

## Metadata
- **Change-ID**: `REQ-TEST-001`
- **Version**: `1.4.0`
- **Status**: `PARTIAL`
- **Last Updated**: 2026-03-19

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

### Requirement: Performance Regression Tracking
The architecture SHALL track execution time and memory usage, flagging regressions exceeding a defined threshold (default: 1.5x baseline).

#### Scenario: Negative - Performance Regression Detected
- **GIVEN** a new version of an implementation that is significantly slower than the previous version
- **WHEN** the Layer 3 tests are run
- **THEN** the runner MUST exit with code `1` and report a `PERFORMANCE_REGRESSION`.

## Design Details

### 1. Architecture Overview
- **Layer 1**: Unit tests (Concrete JSON examples, Oracle validation).
- **Layer 2**: Property-based tests (TOML specifications, Invariant validation).
- **Layer 3**: Performance tests (CSV reports, Regression tracking).

### 2. CLI Interface
**Command:** `elegua-test run --layer [1|2|3]`

**Flags:**
- `--fail-fast`: Stop on first failure.
- `--tolerance <float>`: Override numerical tolerance (default: `1e-12`).
- `--baseline <file>`: CSV file for Layer 3 comparison.

### 3. Data Formats

#### 3.1 Layer 1: Unit Test (TOML)
```toml
[meta]
name = "TransformationTest"

[[tasks]]
action = "Transform"
[tasks.payload]
expression = "input_expression"
```

Test files also support the sxAct extended format with `[[tests]]`, `[[tests.operations]]`, and `[tests.expected]` sections via the bridge loader.

#### 3.2 Layer 3: Performance Report (CSV) — planned
`task_id, duration_ms, memory_mb, tier, timestamp`

### 4. Implementation Status
- **Layer 1 (Unit tests)**: IMPLEMENTED. TOML-based test definitions via `load_toml_tasks()`, `IsolatedRunner`, `MultiTierRunner`. Uses TOML format, not JSON.
- **Layer 2 (Property tests)**: IMPLEMENTED. `PropertyRunner` with PCG64 seeds, `GeneratorRegistry`, TOML spec format. Python API only (no CLI yet).
- **Layer 3 (Performance tests)**: NOT YET IMPLEMENTED. CSV reporting and regression tracking remain future work.
- **CLI (`elegua-test`)**: NOT YET IMPLEMENTED. All functionality is available via Python API.

### 5. Non-Goals
- Real-time profiling (Layer 3 is for coarse-grained regression only).
- Direct code modification or automated fixing.

### 6. Remaining Work
- [ ] Implement `elegua-test` CLI wrapper.
- [ ] Create `perf_tracker.py` for Layer 3 telemetry.
