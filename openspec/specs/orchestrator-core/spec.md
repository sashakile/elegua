# Specification: Eleguá (The Orchestrator)

## Purpose
Eleguá is a domain-agnostic, multi-tier test harness designed to validate the mathematical equivalence of symbolic computing systems during migration (e.g., from Wolfram Mathematica to Julia/Python). It serves as the "Master of the Crossroads," providing an **infrastructure of trust** by orchestrating communication between an **Oracle** (Ground Truth) and one or more **Implementations Under Test (IUT)**.

## Requirements

### Requirement: Multi-Tier Execution
Eleguá SHALL orchestrate the execution of a symbolic task across multiple "Tiers" (Oracle and IUTs) to ensure mathematical parity.

#### Scenario: Verify mathematical equivalence across tiers
- **WHEN** a symbolic action is submitted to Eleguá
- **THEN** it is executed on Tier 1 (Wolfram), Tier 2 (xAct-jl), and Tier 3 (Chacana-jl)
- **AND** the results are compared using the 4-Layer Comparison Pipeline.

### Requirement: Isolated Execution Kernels
Eleguá SHALL ensure that each task is executed in an isolated environment to prevent state leakage.

#### Scenario: Isolated task execution in Wolfram
- **WHEN** a task is executed in the Wolfram Oracle
- **THEN** it is wrapped in a unique `Context` to isolate variables and assignments.

### Requirement: Large Object Handling (Blob Store)
Eleguá SHALL store payloads exceeding 1MB in a dedicated "Blob Store" and reference them by hash in the token to prevent JSON/Pydantic recursion crashes.

#### Scenario: Store large tensor contraction result
- **WHEN** an adapter returns a token larger than 1MB
- **THEN** it is stored using SHA-256 as the hashing algorithm
- **AND** the directory structure MUST use the first two characters of the hash as a sub-directory (e.g., `.elegua/blobs/ab/cd...`).

### Requirement: Standard Error Status Codes
The orchestrator SHALL distinguish between environmental failures and mathematical discrepancies.

#### Scenario: Catch a kernel crash
- **WHEN** an adapter process crashes during execution
- **THEN** it MUST return an `EXECUTION_ERROR` status
- **AND** distinct from a `MATH_MISMATCH` where the results differ.

## Design Details

### 1. The Eleguá Task Lifecycle (`EleguaTask`)
A Task is the atomic unit of validation. It follows a rigorous state machine to ensure reproducibility and isolation.

1.  **Manifest Loading**: Eleguá loads a `Manifest` defining the required environment (packages, versions, resource limits, and warm-up actions).
2.  **Environment Initialization**: Adapters (Tier 1, 2, 3) initialize isolated kernels based on the manifest.
3.  **Warm-up Phase**: Pre-compiles core functions (especially for Julia) to prevent JIT-related timeout flakiness.
4.  **Action Generation**: A `Generator` (static TOML, manual input, or Property-Based Testing engine) emits an `ActionPayload` (JSON).
5.  **Multi-Tier Execution**:
    *   The payload is sent to all active Adapters.
    *   Each Adapter executes the action and returns a `ValidationToken` (JSON-serialized AST).
    *   **Large Object Handling**: Payloads exceeding 1MB are stored in a dedicated "Blob Store" and referenced by hash in the token to prevent JSON/Pydantic recursion crashes.
6.  **Comparison Pipeline**: The tokens are passed through the **4-Layer Comparison** engine.
7.  **Reporting & Cleanup**: Results are logged, and kernels are reset/flushed according to the isolation policy.

### 2. The 4-Layer Comparison Pipeline
To prove mathematical equivalence beyond simple string matching, Eleguá employs a hierarchical validation strategy.

| Layer | Method | Goal | Success Criteria |
| :--- | :--- | :--- | :--- |
| **Layer 1: Identity** | Bitwise / Hash | Instant validation for identical results. | `hash(A) == hash(B)` |
| **Layer 2: Structural** | AST Comparison | Detects structural isomorphism (e.g., `a+b` vs `x+y`). | `Tree(A) ≅ Tree(B)` |
| **Layer 3: Canonical** | **Normalizer** | Semantic equivalence via domain rules (e.g., `a+b` vs `b+a`). | `Norm(A) == Norm(B)` |
| **Layer 4: Invariant** | **Numerical / PBT** | Final mathematical proof via sampling or functional invariants. | `f(A, args) ≈ f(B, args)` |

### 3. Layer 4: Numerical & Property-Based Testing
*   **Numerical Sampling**: If symbolic comparison fails, Eleguá generates random values for free variables.
*   **Pole Handling**: To avoid singularities, sampling employs a **Retry-with-Jitter** strategy. If a pole is detected (`NaN/Inf`), the system re-samples within an "Exclusion Zone" to ensure a valid comparison.
*   **Property-Based Testing (PBT)**: Integration with tools like `Hypothesis` allows Eleguá to generate random symbolic trees (e.g., complex tensor contractions or nested integrals) to find edge cases where implementations diverge from the Oracle.

### 4. Manifest & Isolation Strategy
Eleguá ensures that "ghost state" from previous tests does not pollute subsequent results.

#### 4.1 Manifest Specification (`manifest.toml`)
```toml
[environment]
name = "xAct-Standard-Relativity"
packages = ["xAct`xTensor`"]
version_policy = "strict" # Error if Tier versions mismatch
timeout_per_task = 60
warmup_action = "Contract[DefTensor[T[-a, -b], M]]"

[isolation]
wolfram = "context" # Use unique Contexts (BeginPackage)
julia = "process"   # Use subprocess workers
python = "module"   # Use fresh import machinery

[layers]
numerical_sampling = true
precision_threshold = 1e-12
pole_jitter_radius = 1e-5
max_pbt_examples = 100
```

#### 4.2 Isolation Mechanics
*   **Wolfram (Oracle)**: Every task is wrapped in a unique Mathematica `Context` (e.g., `Task123Scope`). To prevent leakage of `DownValues` or global assignments, the wrapper utilizes `Internal`Bag` patterns or explicit `Unset` cleanup of shared symbols.
    *   **Resilience Fallback**: If the orchestrator detects a "Scope Leak" (via global symbol checksums) or after a configurable number of tasks (e.g., `n=100`), the Oracle kernel is automatically restarted to ensure a hard reset.
*   **Julia (IUT)**: Due to JIT overhead, kernels are kept alive in a pool, but tasks are executed in separate subprocesses or isolated `Module` blocks to prevent global variable leakage.

### 5. The Pluggable Normalizer
The Normalizer is a pluggable strategy that transforms a **ValidationToken** into a **CanonicalToken**.

*   **Registry**: Normalizers are registered via Python entry points.
*   **Oracle-Assisted**: Eleguá can optionally route a result back to the Wolfram Oracle to perform high-level simplification (e.g., `FullSimplify`) before final comparison.
*   **Client-Assisted**: The IUT (e.g., Julia `XPerm`) can provide its own canonical representation as part of the `ValidationToken`.

### 6. Technical Architecture
*   **Language**: Python 3.10+ (generalization of the `sxact` validation framework).
*   **Data Models**: Pydantic for strict schema enforcement. The `ValidationToken` utilizes a **MathJSON-compatible AST structure** to ensure cross-domain expressiveness (Tensors, Integrals, etc.).
*   **Blob Store**: Implements a **Reference-by-Hash** pattern using SHA-256 for large payloads (>1MB). This enables future storage deduplication and offline "Record & Replay" for CI/CD environments without active Oracle licenses.
*   **Status Codes**:
    *   `OK`: Results match across all tiers.
    *   `MATH_MISMATCH`: Kernels completed successfully but results are not equivalent.
    *   `EXECUTION_ERROR`: Kernel or adapter process crashed.
    *   `TIMEOUT`: Execution exceeded `timeout_per_task`.
    *   `SCOPE_LEAK`: Post-task cleanup failed to reset the environment.
*   **IPC**: Support for Subprocesses (standard) and ZMQ/TCP (high-performance persistent kernels).
*   **Extensibility**: Designed to support non-tensor domains (e.g., **RUBI** for integration, **FeynCalc** for particle physics) by swapping the Normalizer and Adapter plugins.
