# Oracle servers

An oracle server wraps a compute kernel (Wolfram, Julia, Sage) in an HTTP server that implements the oracle protocol. The `OracleClient` in the core talks to any server that implements this contract. See [Architecture](../architecture.md) for how oracle servers fit into the three-tier execution model.

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

## Using `elegua[wolfram]`

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

### Configuring for your domain

The Wolfram oracle accepts environment variables for domain-specific setup:

- `ELEGUA_WOLFRAM_INIT` — path to a `.wl` script loaded on first `/evaluate-with-init` call
- `ELEGUA_WOLFRAM_CLEANUP` — Wolfram expression executed on `/cleanup` (defaults to clearing `Global` context)

Example for sxAct (tensor calculus):

```bash
ELEGUA_WOLFRAM_INIT=/opt/xAct/init.wl \
ELEGUA_WOLFRAM_CLEANUP='Manifolds={}; Tensors={}; "cleanup-ok"' \
python -m elegua.wolfram serve
```

## Building your own oracle server

To support a different compute engine, implement the 6 endpoints listed in the protocol table. Use `src/elegua/wolfram/server.py` as a production reference — it is a Flask server with configurable init/cleanup. For testing, the `EchoOracle` provides a minimal implementation:

```python
from elegua.testing import EchoOracle

# Reference implementation that echoes expressions back (no real kernel).
# Useful for testing your client code before the real server exists.
with EchoOracle(port=8765) as oracle:
    print(f"Echo oracle running on {oracle.url}")
```

### Connecting your server to the pipeline

Once your server is running, point `OracleClient` at it and wrap it in a custom adapter. Subclass `Adapter` and delegate to `OracleClient`:

```python
from elegua.adapter import Adapter
from elegua.models import ValidationToken
from elegua.oracle import OracleClient
from elegua.task import EleguaTask, TaskStatus

class MyEngineAdapter(Adapter):
    def __init__(self, base_url: str = "http://localhost:8765") -> None:
        self._client = OracleClient(base_url)

    @property
    def adapter_id(self) -> str:
        return "my-engine"

    def initialize(self) -> None:
        self._client.health_or_raise()

    def teardown(self) -> None:
        self._client.cleanup()

    def execute(self, task: EleguaTask) -> ValidationToken:
        result = self._client.evaluate_with_xact(task.payload["expression"])
        status = TaskStatus.OK if result["status"] == "ok" else TaskStatus.EXECUTION_ERROR
        return ValidationToken(
            adapter_id=self.adapter_id,
            status=status,
            result={"repr": result.get("result", "")},
        )
```

For Wolfram-based engines specifically, use the ready-made `WolframOracleAdapter` instead — see [Writing an adapter](adapters.md) for more on the adapter interface.

## Error recovery

If an evaluation times out or the kernel crashes, the server should automatically restart the kernel and return an error or timeout status. The Wolfram oracle does this: on timeout, it kills the kernel, starts a fresh one, and returns `{"status": "timeout"}`. The `/restart` endpoint provides manual recovery if automatic restart fails.

## Context isolation

When `context_id` is provided in `/evaluate-with-init`, the server should evaluate the expression in an isolated scope so that symbols defined by one test do not leak into another. The Wolfram oracle achieves this with `Block` + `ToExpression` wrapping. Your server can use whatever isolation mechanism your kernel supports.

## Snapshot record and replay

Record oracle responses for offline CI using the snapshot infrastructure:

```bash
ELEGUA_RECORD=1 just test-integration   # records to tests/snapshots/
just test-integration                    # replays from snapshots (no server needed)
```

See `RecordingAdapter` and `ReplayAdapter` in `elegua.snapshot` for details.
