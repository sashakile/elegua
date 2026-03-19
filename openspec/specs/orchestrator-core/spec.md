# Specification: Eleguá (The Orchestrator)

## Metadata
- **Change-ID**: `REQ-ORCH-001`
- **Version**: `1.4.0`
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
Adapters SHALL support explicit lifecycle management via `initialize()` and `teardown()` hooks, with context manager support.

#### Scenario: Adapter lifecycle with context manager
- **GIVEN** an adapter that manages external resources (kernel, connection)
- **WHEN** the adapter is used as a context manager
- **THEN** `initialize()` is called on entry and `teardown()` on exit, even if an exception occurs.

#### Scenario: Negative - Exception in `teardown()` during error handling
- **GIVEN** an adapter whose `teardown()` raises an exception
- **WHEN** the adapter exits due to a primary exception
- **THEN** the `teardown()` exception MUST be suppressed (with a warning) to preserve the original exception.

### Requirement: Oracle Server Protocol
Eleguá SHALL define a standard HTTP contract for oracle servers. Any compute engine that implements this contract can serve as an oracle.

#### Scenario: Oracle health check
- **GIVEN** an oracle server running on a known URL
- **WHEN** `GET /health` is called
- **THEN** the server MUST return `{"status": "ok"}` within 5 seconds.

#### Scenario: Evaluate expression with context isolation
- **GIVEN** an oracle server with a running compute kernel
- **WHEN** `POST /evaluate-with-init` is called with `{"expr": "...", "context_id": "abc123"}`
- **THEN** the expression MUST be evaluated in a `namespace` isolated by `context_id`
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

#### 1.1 `ActionPayload`
The input to an adapter. The `payload` field is an unstructured dict — the format is domain-specific and opaque to the core.
```python
class ActionPayload(BaseModel):
    action: str                    # operation name (e.g., "DefTensor")
    payload: dict[str, Any]        # domain-specific key-value pairs
    domain: str | None = None      # optional domain identifier
    manifest: str | None = None    # optional manifest path
```

#### 1.2 `ValidationToken`
The output from an adapter. The `result` field is an unstructured dict — Eleguá compares results structurally without requiring a fixed AST schema.
```python
class ValidationToken(BaseModel):
    adapter_id: str                # which adapter produced this result
    status: TaskStatus             # OK, MATH_MISMATCH, EXECUTION_ERROR, TIMEOUT
    result: dict[str, Any] | None = None   # domain-specific result payload
    metadata: dict[str, Any] = {}  # timing, diagnostics, etc.
```

#### 1.3 CLI Interface
**Status:** NOT YET IMPLEMENTED. All functionality is available via the Python API (`load_toml_tasks()`, `run_tasks()`, `ComparisonPipeline.compare()`).

**Planned command:** `elegua run [MANIFEST] [ACTION]`

**Planned exit codes:**
- `0`: OK (All tiers match).
- `1`: MATH_MISMATCH.
- `2`: EXECUTION_ERROR.
- `3`: TIMEOUT.

### 2. The Eleguá Task Lifecycle (`EleguaTask`)
1.  **Load**: Parse TOML fixture via `load_toml_tasks()` or `load_sxact_toml()` → list of `EleguaTask` (status: `PENDING`).
2.  **Initialize**: `Adapter.initialize()` sets up kernel/connection (via context manager).
3.  **Execute**: `Adapter.execute(task)` → `ValidationToken` (task transitions: `PENDING → RUNNING → OK | EXECUTION_ERROR | TIMEOUT`).
4.  **Compare**: `ComparisonPipeline.compare(oracle_token, iut_token)` → `ComparisonResult` (layer, status).
5.  **Cleanup**: `Adapter.teardown()` releases resources. `IsolatedRunner` manages per-file lifecycle and per-test binding isolation.

The `MultiTierRunner` orchestrates steps 2-5 for both Oracle and IUT adapters, comparing results per-test.

### 3. The 4-Layer Comparison Pipeline
| Layer | Method | Goal | Success Criteria |
| :--- | :--- | :--- | :--- |
| **Layer 1: Identity** | Structural equality | Instant validation. | `result_a == result_b` |
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

**Context isolation**: When `context_id` is provided, expressions are evaluated in a dedicated scope isolated by that ID. Same `context_id` shares scope; different IDs are isolated. The isolation mechanism is extension-specific (e.g., Wolfram uses `Block` + `ToExpression` wrapping).

**Leak detection**: The `/check-state` endpoint is informational — it reports leaked symbols but does not produce a task status. Leak detection helps test authors identify incomplete cleanup, not task failures.

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

**Wolfram extension configuration** (via environment variables):
- `ELEGUA_WOLFRAM_INIT`: Path to init script loaded on first `/evaluate-with-init` call. No default — the server starts with a bare Wolfram kernel unless configured.
- `ELEGUA_WOLFRAM_CLEANUP`: Wolfram expression executed on `/cleanup`. Defaults to clearing `Global` context only.

Downstream projects (e.g., sxAct) consume the extension and inject domain-specific setup:
```
sxAct (consumer)
├── init.wl (xAct-specific: Needs["xAct`xTensor`"])
├── ELEGUA_WOLFRAM_CLEANUP="Manifolds={}; Tensors={}"
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
