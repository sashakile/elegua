# Oracle servers

**An oracle server exposes a compute kernel over HTTP so Eleguá can execute symbolic actions remotely.**

An oracle server wraps a compute kernel (Wolfram, Julia, Sage) in an HTTP server that implements the oracle protocol.

For new integrations, use `OracleAdapter` — point it at a compatible server, provide any domain-specific expression mapping, and the adapter handles lifecycle and token mapping. See [Architecture](../architecture.md) for how oracle servers fit into the three-tier execution model.

## The oracle protocol

Your server must implement these HTTP endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Return `{"status": "ok"}` within 5 seconds |
| `/evaluate` | POST | Evaluate expression without init script |
| `/evaluate-with-init` | POST | Evaluate with init script loaded, context isolation |
| `/cleanup` | POST | Clear user-defined state between test files |
| `/restart` | POST | Hard-restart the kernel (emergency recovery) |
| `/check-state` | GET | Return `{"clean": true/false, "leaked": [...]}` |

### Request format (`/evaluate-with-init`)

```json
{
  "expr": "1 + 1",
  "timeout": 60,
  "context_id": "optional-unique-id"
}
```

### Response format

```json
{
  "status": "ok",
  "result": "2",
  "timing_ms": 5
}
```

Error response:

```json
{"status": "error", "error": "description of what went wrong"}
```

Timeout response:

```json
{"status": "timeout", "error": "Evaluation timed out after 60s"}
```

The `/evaluate` endpoint uses the same format as `/evaluate-with-init` but without `context_id` or init script loading.

## Wolfram-specific implementation

The `elegua[wolfram]` optional extra ships a ready-made Wolfram kernel oracle server:

```bash
pip install elegua[wolfram]
python -m elegua.wolfram serve --port 8765
```

Or with Docker:

```bash
just oracle-up    # starts on localhost:8765
just oracle-down  # stops the container
```

### Configuring the Wolfram server for your domain

The Wolfram oracle accepts environment variables for domain-specific setup:

- `ELEGUA_WOLFRAM_INIT` — path to a `.wl` script loaded on first `/evaluate-with-init` call
- `ELEGUA_WOLFRAM_CLEANUP` — Wolfram expression executed on `/cleanup` (defaults to clearing `Global` context)

Example for sxAct (tensor calculus):

```bash
ELEGUA_WOLFRAM_INIT=/opt/xAct/init.wl \
ELEGUA_WOLFRAM_CLEANUP='Manifolds={}; Tensors={}; "cleanup-ok"' \
python -m elegua.wolfram serve
```

## Build your own oracle server

To support a different compute engine, implement the 6 endpoints listed in the protocol table. The protocol is the stable contract; the Wolfram server is just one implementation of it. For protocol-level testing, `EchoOracle` provides a minimal implementation:

```python
from elegua.testing import EchoOracle

# Reference implementation that echoes expressions back (no real kernel).
# Useful for testing your client code before the real server exists.
with EchoOracle(port=8765) as oracle:
    print(f"Echo oracle running on {oracle.url}")
```

### Connecting your server to the pipeline

Once your server is running, prefer `OracleAdapter` over building a new
transport adapter from scratch. It already handles health checks, cleanup,
context IDs, timeout mapping, and `ValidationToken` creation.

```python
from elegua.wolfram.adapter import OracleAdapter

adapter = OracleAdapter(
    base_url="http://localhost:8765",
    adapter_id="my-engine",
    expr_builder=lambda action, payload: payload["expression"],
)
```

If your server returns a different response shape, pass a `result_mapper` that
converts the response into a `ValidationToken`:

```python
from elegua.models import ValidationToken
from elegua.task import TaskStatus
from elegua.wolfram.adapter import OracleAdapter

def result_mapper(action: str, payload: dict, data: dict) -> ValidationToken:
    return ValidationToken(
        adapter_id="my-engine",
        status=TaskStatus.OK if data["status"] == "ok" else TaskStatus.EXECUTION_ERROR,
        result={"repr": data.get("result", "")},
        metadata={"execution_time_ms": data.get("timing_ms", 0)},
    )

adapter = OracleAdapter(
    base_url="http://localhost:8765",
    adapter_id="my-engine",
    expr_builder=lambda action, payload: payload["expression"],
    result_mapper=result_mapper,
)
```

!!! note
    `WolframOracleAdapter` is deprecated. Use `OracleAdapter` for new work, even for Wolfram-backed servers.

### When to use `OracleClient` directly

Drop below `OracleAdapter` only if you need transport behavior that the adapter
cannot express. The `OracleClient` method names still reflect the Wolfram-first
history of the module, so it is better treated as a lower-level implementation
detail than as the main extension point for new integrations.

## Error recovery

If an evaluation times out or the kernel crashes, the server should automatically restart the kernel and return an error or timeout status. The Wolfram implementation does this: on timeout, it kills the kernel, starts a fresh one, and returns `{"status": "timeout"}`. The `/restart` endpoint provides manual recovery if automatic restart fails.

## Context isolation

When `context_id` is provided in `/evaluate-with-init`, the server should evaluate the expression in an isolated scope so that symbols defined by one test do not leak into another. The Wolfram implementation achieves this with `Block` + `ToExpression` wrapping. Your server can use whatever isolation mechanism your kernel supports.

## Snapshot record and replay

Record oracle responses for offline CI using the snapshot infrastructure:

```bash
ELEGUA_RECORD=1 just test-integration   # records to tests/snapshots/
just test-integration                    # replays from snapshots (no server needed)
```

See `RecordingAdapter` and `ReplayAdapter` in `elegua.snapshot` for details.
