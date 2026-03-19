# Specification: Eleguá (The Orchestrator)

## Metadata
- **Change-ID**: `REQ-ORCH-001`
- **Version**: `1.3.0`
- **Status**: `IMPLEMENTED`
- **Last Updated**: 2026-03-19

## Purpose
Eleguá is a domain-agnostic, multi-tier test harness designed to validate the mathematical equivalence of symbolic computing systems during migration or reimplementation. It serves as a generic **infrastructure of trust** by orchestrating communication between a **High-Fidelity Oracle** (Ground Truth) and one or more **Implementations Under Test (IUT)**.

## Requirements

### Requirement: Multi-Tier Execution
Eleguá SHALL execute a symbolic task across multiple "Tiers" (Oracle and IUTs) to ensure mathematical parity.

#### Scenario: Verify mathematical equivalence across tiers
- **GIVEN** a task manifest defining Tier 1 (Oracle) and Tier 2 (IUT)
- **WHEN** a symbolic action is submitted to Eleguá
- **THEN** it is executed on both tiers
- **AND** the results are compared using the 4-Layer Comparison Pipeline.

#### Scenario: Negative - Execution Error
- **GIVEN** a task where an IUT crashes
- **WHEN** the action is executed
- **THEN** Eleguá MUST return an `EXECUTION_ERROR` for that tier and continue if configured.

### Requirement: Isolated Execution Kernels
Eleguá SHALL ensure that each task is executed in an isolated environment to prevent state leakage.

#### Scenario: Isolated task execution via Scope/Context
- **GIVEN** an adapter supporting logical isolation
- **WHEN** a task is executed
- **THEN** it is wrapped in a unique logical context to isolate variables and assignments.

#### Scenario: Isolated task execution via Subprocess
- **GIVEN** an adapter supporting process isolation
- **WHEN** a task is executed
- **THEN** it is run in a fresh subprocess worker.

### Requirement: Adapter Lifecycle
Adapters SHALL support explicit lifecycle management via `initialize()` and `tear-down()` hooks, with context manager support.

#### Scenario: Adapter lifecycle with context manager
- **GIVEN** an adapter that manages external resources (kernel, connection)
- **WHEN** the adapter is used as a context manager
- **THEN** `initialize()` is called on entry and `tear-down()` on exit, even if an exception occurs.

#### Scenario: Negative - Tear-down exception during error handling
- **GIVEN** an adapter whose `tear-down()` raises an exception
- **WHEN** the adapter exits due to a primary exception
- **THEN** the tear-down exception MUST be suppressed (with a warning) to preserve the original exception.

### Requirement: Oracle Server Protocol
Eleguá SHALL define a standard HTTP contract for oracle servers. Any compute engine that implements this contract can serve as an oracle.

#### Scenario: Oracle health check
- **GIVEN** an oracle server running on a known URL
- **WHEN** `GET /health` is called
- **THEN** the server MUST return `{"status": "ok"}` within 5 seconds.

#### Scenario: Evaluate expression with context isolation
- **GIVEN** an oracle server with a running compute kernel
- **WHEN** `POST /evaluate-with-init` is called with `{"expr": "...", "context_id": "abc123"}`
- **THEN** the expression MUST be evaluated in a name space isolated by `context_id`
- **AND** the response MUST include `status`, `result`, and `timing_ms`.

#### Scenario: Cleanup between test files
- **GIVEN** an oracle server with accumulated state from previous tests
- **WHEN** `POST /cleanup` is called
- **THEN** the server MUST clear user-defined state (configurable per domain)
- **AND** return `{"status": "ok"}`.

#### Scenario: State leak detection
- **GIVEN** an oracle server after cleanup
- **WHEN** `GET /check-state` is called
- **THEN** the server MUST return `{"clean": true/false, "leaked": [...]}`.

### Requirement: Extension Model
Domain-specific oracle servers SHALL be shipped as optional extras (`pip install elegua[<engine>]`), not as part of the core.

#### Scenario: Install Wolfram oracle extension
- **GIVEN** a user who needs to validate against a Wolfram kernel
- **WHEN** they install `pip install elegua[wolfram]`
- **THEN** they get the Wolfram oracle HTTP server, `WolframOracleAdapter`, and a Docker image template.

#### Scenario: Configurable domain-specific initialization
- **GIVEN** a generic Wolfram oracle server from `elegua[wolfram]`
- **WHEN** a downstream project (e.g., sxAct) sets `ELEGUA_WOLFRAM_INIT=/path/to/init.wl`
- **THEN** the server MUST load that init script on kernel startup
- **AND** the server MUST use `ELEGUA_WOLFRAM_CLEANUP` for domain-specific cleanup commands.

### Requirement: Large Object Handling (Blob Store)
Eleguá SHALL store payloads exceeding 1MB in a dedicated "Blob Store" and reference them by hash in the token.

#### Scenario: Store large symbolic result
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
  "action": "TransformationName",
  "domain": "SymbolicDomain",
  "manifest": "manifest.toml",
  "payload": {
    "expression": { "fn": "Operator", "args": [...] }
  }
}
```

#### 1.2 ValidationToken (MathJSON AST)
The output from an adapter.
```json
{
  "adapter_id": "adapter-tier1",
  "status": "OK",
  "result": {
    "fn": "Operator",
    "args": [...]
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
| **Layer 3: Canonical** | **Normalizer** | Semantic equivalence via pluggable rules. | `Norm(A) == Norm(B)` |
| **Layer 4: Invariant** | **Numerical / PBT** | Mathematical proof via domain-specific invariants. | `f(A, args) ≈ f(B, args)` |

### 4. Oracle Server Contract

The oracle server is a lightweight HTTP server wrapping a compute kernel. Eleguá defines the protocol; extensions implement it.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check (5s timeout) |
| `/evaluate` | POST | Evaluate expression without init script |
| `/evaluate-with-init` | POST | Evaluate with init script loaded, context isolation |
| `/cleanup` | POST | Clear user-defined state between test files |
| `/restart` | POST | Hard-restart kernel (emergency recovery) |
| `/check-state` | GET | Detect leaked symbols after cleanup |

**Configuration** (via environment variables):
- `ELEGUA_WOLFRAM_INIT`: Path to init script loaded on first `/evaluate-with-init` call.
- `ELEGUA_WOLFRAM_CLEANUP`: Wolfram expression executed on `/cleanup`. Defaults to clearing `Global` context only. Downstream projects inject domain-specific cleanup (e.g., clearing xAct registries).

**Context isolation**: When `context_id` is provided, expressions are evaluated in a dedicated name space (`Block` + `ToExpression` wrapping). Same `context_id` shares name space; different IDs are isolated.

**Thread safety**: The server serializes kernel access via a lock and single-threaded executor. Concurrent HTTP requests queue to the kernel sequentially.

### 5. Extension Architecture

```
elegua (core)                    elegua[wolfram] (optional extra)
├── OracleClient (HTTP client)   ├── WolframOracleAdapter
├── Adapter ABC                  ├── server.py (Flask HTTP server)
├── ComparisonPipeline           ├── kernel.py (WSTP kernel manager)
├── IsolatedRunner               ├── Docker image
└── MultiTierRunner              └── __main__.py (CLI entry point)
```

Downstream projects (e.g., sxAct) consume the extension:
```
sxAct (consumer)
├── init.wl (xAct-specific initialization)
├── cleanup config (clear Manifolds, Tensors registries)
├── xact_builder.py (domain-specific expression builder)
└── depends on: elegua[wolfram]
```

### 6. Non-Goals
- Real-time interactive execution (designed for batch validation).
- Direct modification of source code (read-only verification).
- Domain-specific logic in the core (injected via adapters and init scripts).

### 7. Technical Architecture
- **Language**: Python 3.11+
- **Data Models**: Pydantic
- **Transport**: HTTP (oracle protocol). ZMQ/TCP deferred until a concrete consumer requires it.
- **Status Codes**: `OK`, `MATH_MISMATCH`, `EXECUTION_ERROR`, `TIMEOUT`.
