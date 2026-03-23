# Specification: Eleguá (The Orchestrator)

## Metadata
- **Change-ID**: `REQ-ORCH-001`
- **Version**: `1.5.0`
- **Status**: `IMPLEMENTED`
- **Last Updated**: 2026-03-23

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

### Requirement: Execution Context and Reference Resolution
Eleguá SHALL provide a variable binding store that supports `$name` reference substitution and scoped binding isolation across setup and test phases.

#### Scenario: Store and resolve a reference
- **GIVEN** an operation with `store_as = "antideriv"` that returns a result with `repr`
- **WHEN** a subsequent operation has `expression = "$antideriv"` in its args
- **THEN** the `$antideriv` reference MUST be replaced with the stored `repr` value.

#### Scenario: Setup bindings are file-wide; test bindings are per-test
- **GIVEN** a test file with setup operations that store bindings
- **WHEN** multiple tests execute within the same file
- **THEN** each test MUST see the setup bindings
- **AND** bindings created within one test MUST NOT leak to other tests.

#### Scenario: Unresolved reference emits a warning
- **GIVEN** a payload containing `$unknown` where no binding exists
- **WHEN** reference resolution is performed
- **THEN** the reference MUST be left as-is and a `RuntimeWarning` emitted.

### Requirement: Snapshot Record/Replay
Eleguá SHALL support recording adapter results to a persistent store and replaying them without a live oracle, enabling offline CI.

#### Scenario: Record oracle results for replay
- **GIVEN** a `RecordingAdapter` wrapping a live adapter
- **WHEN** tasks are executed
- **THEN** each `ValidationToken` MUST be persisted in a `SnapshotStore` keyed by SHA-256 of `action + payload`.

#### Scenario: Replay cached results without oracle
- **GIVEN** a `ReplayAdapter` loaded from a `SnapshotStore`
- **WHEN** a task is executed whose key exists in the store
- **THEN** the cached `ValidationToken` MUST be returned without contacting any oracle.

#### Scenario: Negative - Replay cache miss
- **GIVEN** a `ReplayAdapter` with no snapshot for a task
- **WHEN** the task is executed
- **THEN** it MUST return a `ValidationToken` with `EXECUTION_ERROR` status and a descriptive error in `metadata`.

### Requirement: Domain Exception Hierarchy
Eleguá SHALL define a structured exception hierarchy rooted at `EleguaError` so that callers can catch all library errors with a single `except EleguaError`.

#### Scenario: Catch any elegua error
- **GIVEN** code that catches `EleguaError`
- **WHEN** any elegua-specific error is raised (schema, adapter, oracle)
- **THEN** it MUST be caught by the `except EleguaError` handler.

#### Scenario: SchemaError is also a ValueError
- **GIVEN** code that catches `ValueError`
- **WHEN** a `SchemaError` is raised (e.g., invalid TOML)
- **THEN** it MUST be caught by the `except ValueError` handler for backward compatibility.

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

### 1. Domain Exception Hierarchy

All exceptions inherit from `EleguaError`:

```
EleguaError
├── SchemaError (also inherits ValueError)
│   └── TOML parsing, Pydantic validation, invalid identifiers
├── AdapterError
│   └── Adapter execution failures
│       └── OracleError
│           └── Oracle-specific HTTP/protocol failures
└── PropertyValidationError
    └── Invalid property spec schemas
```

**Operational vs programming errors**: `IsolatedRunner` catches operational errors (`OSError`, `ConnectionError`, `RuntimeError`, `TimeoutError`, `ValueError`) and records them as test errors. Programming errors (`TypeError`, `AttributeError`, etc.) propagate immediately — they indicate bugs, not test failures.

### 2. Interfaces & Data Models

#### 2.1 `ActionPayload`
The input to an adapter. The `payload` field is an unstructured dict — the format is domain-specific and opaque to the core.
```python
class ActionPayload(BaseModel):
    action: str                    # operation name (e.g., "DefTensor")
    payload: dict[str, Any]        # domain-specific key-value pairs
    domain: str | None = None      # optional domain identifier
    manifest: str | None = None    # optional manifest path
```

#### 2.2 `ValidationToken`
The output from an adapter. The `result` field is an unstructured dict — Eleguá compares results structurally without requiring a fixed AST schema.
```python
class ValidationToken(BaseModel):
    adapter_id: str                # which adapter produced this result
    status: TaskStatus             # OK, MATH_MISMATCH, EXECUTION_ERROR, TIMEOUT
    result: dict[str, Any] | None = None   # domain-specific result payload
    metadata: dict[str, Any] = {}  # timing, diagnostics, etc.
```

##### Extended `result` Schema

The `result` dict is domain-specific, but adapters targeting cross-CAS verification SHOULD include these optional fields:

| Field | Type | Description |
|-------|------|-------------|
| `repr` | `str` | Canonical string representation of the result |
| `numeric_samples` | `list[{vars: dict[str, float], value: float}]` | Numerical evaluations at sample points for L4 comparison |

**`numeric_samples`**: A list of point evaluations used by L4 (numeric/invariant) comparison. Each entry maps variable names to values and records the function value at that point. This field is **excluded from L1 and L2 comparison** — it carries data for higher-layer verification only.

Example:
```json
{
  "repr": "x^3/3",
  "numeric_samples": [
    {"vars": {"x": 1.0}, "value": 0.333},
    {"vars": {"x": 2.0}, "value": 2.667}
  ]
}
```

#### 2.3 CLI Interface
**Status:** NOT YET IMPLEMENTED. All functionality is available via the Python API (`load_toml_tasks()`, `run_tasks()`, `ComparisonPipeline.compare()`).

**Planned command:** `elegua run [MANIFEST] [ACTION]`

**Planned exit codes:**
- `0`: OK (All tiers match).
- `1`: MATH_MISMATCH.
- `2`: EXECUTION_ERROR.
- `3`: TIMEOUT.

### 3. The Eleguá Task Lifecycle (`EleguaTask`)
1.  **Load**: Parse TOML fixture via `load_toml_tasks()` or `load_sxact_toml()` → list of `EleguaTask` (status: `PENDING`).
2.  **Initialize**: `Adapter.initialize()` sets up kernel/connection (via context manager).
3.  **Execute**: `Adapter.execute(task)` → `ValidationToken` (task transitions: `PENDING → RUNNING → OK | EXECUTION_ERROR | TIMEOUT`).
4.  **Compare**: `ComparisonPipeline.compare(oracle_token, iut_token)` → `ComparisonResult` (layer, status).
5.  **Cleanup**: `Adapter.teardown()` releases resources. `IsolatedRunner` manages per-file lifecycle and per-test binding isolation.

The `MultiTierRunner` orchestrates steps 2-5 for both Oracle and IUT adapters, comparing results per-test.

### 4. The 4-Layer Comparison Pipeline

| Layer | Method | Goal | Success Criteria |
| :--- | :--- | :--- | :--- |
| **Layer 1: Identity** | Structural equality | Instant validation. | `result_a == result_b` |
| **Layer 2: Structural** | AST Comparison | Detects isomorphism. | `Tree(A) ≅ Tree(B)` |
| **Layer 3: Canonical** | **Normalizer** | Semantic equivalence via pluggable rules. | `Norm(A) == Norm(B)` |
| **Layer 4: Invariant** | **Numerical / PBT** | Mathematical proof via domain-specific invariants. | `f(A, args) ≈ f(B, args)` |

The pipeline runs layers in ascending order, **stopping at the first match** (OK). If no layer matches, the result is `MATH_MISMATCH` at the last layer attempted. Layers are registered via `ComparisonPipeline.register(layer_num, name, fn)` — duplicate layer numbers raise `SchemaError`.

**L1/L2 are built-in** and registered by default. Keys in `_L4_KEYS` (currently `{"numeric_samples"}`) are stripped from results before L1/L2 comparison so that L4-only data does not interfere with structural matching.

**L3 (Canonical)** is a pluggable slot. Domain-specific normalizers (e.g., tensor index canonicalizers) are registered by the caller. The normalizer function signature is `(ValidationToken, ValidationToken) → TaskStatus`.

**L4 (Numeric)** is provided by `make_numeric_comparator(tol, min_samples)`, a factory that returns a `LayerFn` closure. It matches sample points from `numeric_samples` by their `vars` dict, then checks that `value` fields agree within absolute `tol`. Returns `MATH_MISMATCH` if fewer than `min_samples` common points exist.

```python
from elegua.compare_numeric import make_numeric_comparator

pipeline = ComparisonPipeline()
pipeline.register(4, "numeric", make_numeric_comparator(tol=1e-6, min_samples=2))
```

### 5. Execution Context (`ExecutionContext`)

The `ExecutionContext` is a mutable name-to-value store used by `IsolatedRunner` to chain operation results via `store_as` / `$ref`.

**Binding lifecycle**:
1. Setup operations run first; their `store_as` bindings become the **setup snapshot**.
2. Before each test, the context is **restored** to the setup snapshot (per-test isolation).
3. Test operations can `store_as` within their scope; these bindings are discarded after the test.

**Reference resolution**: `resolve_refs(payload)` substitutes `$name` tokens in top-level string values of the payload dict using regex `\$(\w+)`. Non-string values pass through unchanged. Unresolved references are left as-is with a `RuntimeWarning`.

**`store_as` extraction**: When an operation has `store_as` set, `IsolatedRunner` stores `token.result["repr"]` (or `str(token.result)` if `repr` is absent) under that name. If `token.result` is `None`, a `RuntimeWarning` is emitted and the binding is skipped.

### 6. Snapshot Record/Replay

Enables offline CI by recording oracle responses and replaying them without a live kernel.

**`SnapshotStore`**: Persists `ValidationToken` objects keyed by deterministic SHA-256 of `action + "|" + json.dumps(payload, sort_keys=True)`. Backed by a JSON file with structure `{"snapshots": {key: token_dict, ...}}`. Corrupt JSON raises `SchemaError`.

**`RecordingAdapter`**: Decorator wrapping any `Adapter`. Delegates `initialize()`, `execute()`, and `teardown()` to the inner adapter. On `execute()`, saves the returned token to the store. On `teardown()`, persists the store to disk.

**`ReplayAdapter`**: Standalone adapter (`adapter_id = "replay"`) that looks up tasks in a `SnapshotStore`. Cache miss returns `EXECUTION_ERROR` with descriptive metadata — it does not raise an exception.

```python
# Record
store = SnapshotStore(Path("snapshots/oracle.json"))
with IsolatedRunner(RecordingAdapter(live_adapter, store)):
    results = runner.run(test_file)

# Replay (no oracle needed)
store = SnapshotStore.read(Path("snapshots/oracle.json"))
with IsolatedRunner(ReplayAdapter(store)):
    results = runner.run(test_file)
```

### 7. Oracle Server Contract

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

### 8. Extension Architecture

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

### 9. Adapter Guidelines for Cross-CAS Verification

Adapters that target cross-CAS verification (e.g., Wolfram vs Julia) SHOULD follow these conventions for `ValidationToken.result`:

1. **Always include `repr`**: A canonical string form of the result. This is what L1/L2 comparison and verdict evaluation use.
2. **Include `numeric_samples` when feasible**: Sample the result expression at representative points. This enables L4 numeric comparison to verify mathematical equivalence even when string representations differ across CAS backends.
3. **Keep `numeric_samples` out of structural identity**: The core strips `numeric_samples` before L1 and L2 comparison. Adapters can return different sample points without affecting structural match results.
4. **Use consistent variable naming**: Sample point variables (`vars` keys) should match the variable names used in the original expression so L4 can align samples across adapters.

### 10. Verification Patterns

#### Integrate-then-Differentiate (RUBI Pattern)

The standard verification strategy for integration rules. Works with any CAS backend using the existing `store_as` + `$ref` mechanism in TOML test files — no code changes required.

**Pattern:**
1. **Integrate** the expression, store the antiderivative via `store_as`
2. **Differentiate** the stored antiderivative using `$ref`
3. **Assert** the result matches the original integrand via `expected.expr`

**TOML structure:**
```toml
[[tests]]
id          = "integrate_x_squared"
description = "Power rule round-trip"

[[tests.operations]]
action   = "Integrate"
store_as = "antideriv"
[tests.operations.args]
expression = "x^2"
variable   = "x"

[[tests.operations]]
action   = "Differentiate"
store_as = "result"
[tests.operations.args]
expression = "$antideriv"
variable   = "x"

[tests.expected]
expr = "x^2"
```

**How it works:**
- The `Integrate` operation sends `{"expression": "x^2", "variable": "x"}` to the adapter. The adapter returns a `ValidationToken` with `result.repr` (e.g., `"x^3/3"`). The `store_as` mechanism stores this repr as `antideriv`.
- The `Differentiate` operation resolves `$antideriv` to the stored value and sends it to the adapter. The adapter returns the derivative, which should equal the original integrand.
- The `expected.expr` check in the verdict system verifies the round-trip.

**Why this works across CAS backends:** Each backend may represent the antiderivative differently (e.g., `x^3/3` vs `Power[x,3]/3`), but differentiation is a well-defined operation. The round-trip `d/dx(integral(f)) == f` is the mathematical invariant, independent of representation.

**Example files:** See `tests/fixtures/rubi_power.toml`, `rubi_trig.toml`, `rubi_exp.toml`.

### 11. Non-Goals
- Real-time interactive execution (designed for batch validation).
- Direct modification of source code (read-only verification).
- Domain-specific logic in the core (injected via adapters and init scripts).

### 12. Technical Architecture
- **Language**: Python 3.11+
- **Data Models**: Pydantic
- **Transport**: HTTP (oracle protocol). ZMQ/TCP deferred until a concrete consumer requires it.
- **Status Codes**: `OK`, `MATH_MISMATCH`, `EXECUTION_ERROR`, `TIMEOUT`.
