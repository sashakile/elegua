# Specification: Eleguá (The Orchestrator)

## Metadata
- **Change-ID**: `REQ-ORCH-001`
- **Version**: `1.1.0`
- **Status**: `PROPOSAL`
- **Last Updated**: 2026-03-17

## Purpose
Eleguá is a domain-agnostic, multi-tier test harness designed to validate the mathematical equivalence of symbolic computing systems during migration (e.g., from Wolfram Mathematica to Julia/Python). It serves as the "Master of the Crossroads," providing an **infrastructure of trust** by orchestrating communication between an **Oracle** (Ground Truth) and one or more **Implementations Under Test (IUT)**.

## Requirements

### Requirement: Multi-Tier Execution
Eleguá SHALL execute a symbolic task across multiple "Tiers" (Oracle and IUTs) to ensure mathematical parity.

#### Scenario: Verify mathematical equivalence across tiers
- **GIVEN** a task manifest defining Tier 1, 2, and 3
- **WHEN** a symbolic action is submitted to Eleguá
- **THEN** it is executed on Tier 1 (Wolfram), Tier 2 (xAct-jl), and Tier 3 (Chacana-jl)
- **AND** the results are compared using the 4-Layer Comparison Pipeline.

#### Scenario: Negative - Execution Error
- **GIVEN** a task where Tier 2 crashes
- **WHEN** the action is executed
- **THEN** Eleguá MUST return an `EXECUTION_ERROR` for Tier 2 and continue if configured.

### Requirement: Isolated Execution Kernels
Eleguá SHALL ensure that each task is executed in an isolated environment to prevent state leakage.

#### Scenario: Isolated task execution in Wolfram
- **GIVEN** a Wolfram adapter
- **WHEN** a task is executed
- **THEN** it is wrapped in a unique `Context` to isolate variables and assignments.

#### Scenario: Isolated task execution in Julia
- **GIVEN** a Julia adapter
- **WHEN** a task is executed
- **THEN** it is run in a fresh subprocess worker.

### Requirement: Large Object Handling (Blob Store)
Eleguá SHALL store payloads exceeding 1MB in a dedicated "Blob Store" and reference them by hash in the token.

#### Scenario: Store large tensor contraction result
- **GIVEN** a result exceeding 1MB
- **WHEN** the adapter returns the token
- **THEN** the payload is stored using SHA-256 in `.elegua/blobs/[ab]/[cd...]`
- **AND** the token contains `{"blob": "<hash>"}`.

#### Scenario: Negative - Blob Store Write Failure
- **GIVEN** a full disk or permission error
- **WHEN** storing a large payload
- **THEN** the runner MUST raise an `IOError` and exit with code `2`.

## Design Details

### 1. Interfaces & Data Models

#### 1.1 ActionPayload (JSON)
The input to an adapter.
```json
{
  "action": "ToCanonical",
  "domain": "Tensor",
  "manifest": "manifest.toml",
  "payload": {
    "expression": { "fn": "Add", "args": [...] }
  }
}
```

#### 1.2 ValidationToken (MathJSON AST)
The output from an adapter.
```json
{
  "adapter_id": "wolfram-tier1",
  "status": "OK",
  "result": {
    "fn": "Power",
    "args": [{"sym": "x"}, 2]
  },
  "metadata": { "duration_ms": 120 }
}
```

#### 1.3 CLI Interface
**Command:** `elegua run [MANIFEST] [ACTION]`

**Exit Codes:**
- `0`: OK (All tiers match).
- `1`: MATH_MISMATCH.
- `2`: EXECUTION_ERROR / INFRA_ERROR.
- `3`: TIMEOUT.

### 2. The Eleguá Task Lifecycle (`EleguaTask`)
1.  **Manifest Loading**: Load `manifest.toml`.
2.  **Environment Initialization**: Initialize isolated kernels.
3.  **Warm-up Phase**: Pre-compile/load core libraries.
4.  **Action Generation**: Emit `ActionPayload`.
5.  **Multi-Tier Execution**: Collect `ValidationToken` from each tier.
6.  **Comparison Pipeline**: Pass through 4-Layer Engine.
7.  **Reporting**: Log and cleanup.

### 3. The 4-Layer Comparison Pipeline
| Layer | Method | Goal | Success Criteria |
| :--- | :--- | :--- | :--- |
| **Layer 1: Identity** | Bitwise / Hash | Instant validation. | `hash(A) == hash(B)` |
| **Layer 2: Structural** | AST Comparison | Detects isomorphism. | `Tree(A) ≅ Tree(B)` |
| **Layer 3: Canonical** | **Normalizer** | Semantic equivalence. | `Norm(A) == Norm(B)` |
| **Layer 4: Invariant** | **Numerical / PBT** | Mathematical proof. | `f(A, args) ≈ f(B, args)` |

### 4. Non-Goals
- Real-time interactive execution (designed for batch validation).
- Direct modification of source code (read-only verification).

### 5. Technical Architecture
- **Language**: Python 3.10+
- **Data Models**: Pydantic
- **IPC**: Subprocesses, ZMQ/TCP.
- **Status Codes**: `OK`, `MATH_MISMATCH`, `EXECUTION_ERROR`, `TIMEOUT`, `SCOPE_LEAK`.
