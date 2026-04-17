# Task lifecycle

**`EleguaTask` carries an action through an enforced state machine so you can track execution from `PENDING` to a terminal verdict.**

`ValidationToken` is what adapters return after execution.

## EleguaTask

The `EleguaTask` is the atomic unit of validation. It carries an action name, a payload dict, and tracks its execution status.

```python
from elegua.task import EleguaTask, TaskStatus

task = EleguaTask(action="DefTensor", payload={"name": "T", "indices": ["a", "b"]})
print(task.id)      # auto-generated UUID
print(task.status)  # TaskStatus.PENDING
```

## State machine

Tasks follow a strict lifecycle enforced by `transition()`:

```
PENDING → RUNNING → OK
                  → MATH_MISMATCH
                  → EXECUTION_ERROR
                  → TIMEOUT
```

All terminal states (OK, MATH_MISMATCH, EXECUTION_ERROR, TIMEOUT) reject further transitions.

```python
running = task.transition(TaskStatus.RUNNING)
completed = running.transition(TaskStatus.OK)

# Invalid transitions raise InvalidTransition
task.transition(TaskStatus.OK)  # raises: cannot go from PENDING to OK
```

!!! important
    `transition()` returns a **new** task. The original is never mutated.

## ActionPayload and ValidationToken

These are the spec-defined interchange models.

`ActionPayload` is a spec-level type that describes the input to an adapter. In most workflows you won't construct one yourself — the runner builds `EleguaTask` objects from TOML and passes them directly to `Adapter.execute()`. `ActionPayload` exists for tooling and serialization scenarios where you need a standalone input envelope.

```python
from elegua.models import ActionPayload

payload = ActionPayload(
    action="DefTensor",
    payload={"name": "T"},
    domain="tensor_calculus",
    manifest="manifest.toml",
)
```

`ValidationToken` is what adapters return after execution. You interact with these directly when comparing results:

```python
from elegua.models import ValidationToken
from elegua.task import TaskStatus

token = ValidationToken(
    adapter_id="wolfram",
    status=TaskStatus.OK,
    result={"fn": "Tensor", "args": ["a", "b"]},
    metadata={"execution_time_ms": 120},
)
```

## Next steps

- [Writing an adapter](adapters.md) — connect Eleguá to your own symbolic engine
- [Blob store](blob-store.md) — how large `result` payloads are offloaded to disk automatically
