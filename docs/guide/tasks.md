# Task lifecycle

`EleguaTask` carries an action through a state machine from `PENDING` to a terminal verdict. `ValidationToken` is what adapters return after execution.

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

These are the spec-defined interchange models:

```python
from elegua.models import ActionPayload, ValidationToken

# Input to an adapter
payload = ActionPayload(
    action="DefTensor",
    payload={"name": "T"},
    domain="tensor_calculus",
    manifest="manifest.toml",
)

# Output from an adapter
token = ValidationToken(
    adapter_id="wolfram",
    status=TaskStatus.OK,
    result={"fn": "Tensor", "args": ["a", "b"]},
    metadata={"duration_ms": 120},
)
```

## Next steps

See [Writing an adapter](adapters.md) to connect Eleguá to your own symbolic engine.
