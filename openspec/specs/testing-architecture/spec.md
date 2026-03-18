# Specification: Three-Layer Testing Architecture

## Metadata
- **Change-ID**: `REQ-TEST-001`
- **Version**: `1.1.0`
- **Status**: `PROPOSAL`
- **Last Updated**: 2026-03-17

## Purpose
This specification defines the three-layer testing architecture for the xAct migration project. It ensures that the migration from Wolfram Mathematica to Julia and Python is mathematically correct, performant, and serves as a foundation for language-agnostic mathematical property specifications.

## Requirements

### Requirement: Migration Validation
The testing architecture SHALL validate the functional equivalence and performance of the migrated implementation against the Wolfram xAct oracle using a default numerical tolerance of `1e-12`.

#### Scenario: Validate tensor contraction
- **GIVEN** a tensor contraction task
- **WHEN** it is executed in Julia (Tier 2/3)
- **THEN** the result MUST match the Wolfram xAct oracle (Tier 1) within `1e-12` relative tolerance.

#### Scenario: Negative - Verification Failure
- **GIVEN** a task where the results diverge beyond `1e-12`
- **WHEN** the comparison is performed
- **THEN** the runner MUST report a `MATH_MISMATCH` and output the delta.

### Requirement: Language-Agnostic Property Specification
The architecture SHALL support property-based tests that describe mathematical laws independent of the specific implementation language.

#### Scenario: Verify associativity of tensor contraction
- **GIVEN** a property test defining associativity
- **WHEN** it is run across Wolfram, Julia, and Python
- **THEN** it MUST hold for 100 random samples.

### Requirement: Performance Regression Tracking
The architecture SHALL track execution time and memory usage, flagging regressions exceeding 1.5x the baseline.

#### Scenario: Negative - Performance Regression Detected
- **GIVEN** a new version of XTensor.jl that is 2x slower than the previous version
- **WHEN** the Layer 3 tests are run
- **THEN** the runner MUST exit with code `1` and report a `PERFORMANCE_REGRESSION`.

## Design Details

### 1. Architecture Overview
- **Layer 1**: Unit tests (Concrete JSON examples, Oracle validation).
- **Layer 2**: Property-based tests (TOML specifications, Invariant validation).
- **Layer 3**: Performance tests (CSV reports, Regression tracking).

### 2. CLI Interface
**Command:** `xact-test run --layer [1|2|3]`

**Flags:**
- `--fail-fast`: Stop on first failure.
- `--tolerance <float>`: Override numerical tolerance (default: `1e-12`).
- `--baseline <file>`: CSV file for Layer 3 comparison.

### 3. Data Formats

#### 3.1 Layer 1: Unit Test (JSON)
```json
{
  "name": "SymmetricSwap",
  "action": "ToCanonical",
  "input": { "fn": "Sub", "args": [...] },
  "expected": "0"
}
```

#### 3.2 Layer 3: Performance Report (CSV)
`task_id, duration_ms, memory_mb, tier, timestamp`

### 4. Non-Goals
- Real-time profiling (Layer 3 is for coarse-grained regression only).
- Mutation testing (superseded by Oracle/PBT validation).

### 5. Task Readiness
- [ ] Implement `xact-test` CLI wrapper.
- [ ] Integrate `sampling.py` for Layer 2.
- [ ] Create `perf_tracker.py` for Layer 3 telemetry.
