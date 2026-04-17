# Writing an adapter

**Subclass `Adapter` and implement `execute()` so Eleguá can talk to your symbolic engine.**

Each adapter translates an `EleguaTask` into a call to its engine and returns a `ValidationToken` with the result.

## The Adapter interface

Subclass `Adapter` and implement two members:

- `adapter_id` — a unique string identifying this adapter
- `execute()` — run the task and return a `ValidationToken`

```python
from elegua.adapter import Adapter
from elegua.models import ValidationToken
from elegua.task import EleguaTask, TaskStatus

class MyAdapter(Adapter):
    @property
    def adapter_id(self) -> str:
        return "my-engine"

    def execute(self, task: EleguaTask) -> ValidationToken:
        # Send task.action and task.payload to your engine
        result = my_engine.run(task.action, task.payload)
        return ValidationToken(
            adapter_id=self.adapter_id,
            status=TaskStatus.OK,
            result=result,
        )
```

!!! warning
    `execute()` must **not** mutate the input `EleguaTask`. Return a `ValidationToken` with the result; the original task stays unchanged.

## Run a complete comparison with your adapter

This example is copy-pasteable as written. It creates one task, runs it through
the built-in `WolframAdapter` stub and a custom adapter, and compares the two
results through the default pipeline.

```python
from elegua.adapter import Adapter, WolframAdapter
from elegua.comparison import compare_pipeline
from elegua.models import ValidationToken
from elegua.task import EleguaTask, TaskStatus

class MyAdapter(Adapter):
    @property
    def adapter_id(self) -> str:
        return "my-engine"

    def execute(self, task: EleguaTask) -> ValidationToken:
        # Replace this echo behavior with a call into your real engine.
        return ValidationToken(
            adapter_id=self.adapter_id,
            status=TaskStatus.OK,
            result=task.payload,
        )

task = EleguaTask(action="Echo", payload={"expr": "x + y"})

with WolframAdapter() as oracle, MyAdapter() as iut:
    oracle_token = oracle.execute(task)
    iut_token = iut.execute(task)

result = compare_pipeline(oracle_token, iut_token)
print(result.layer, result.layer_name, result.status.value)
```

Expected output:

```text
1 identity ok
```

Because both adapters return the same payload, the comparison succeeds at layer
1. If your adapter produces a different but mathematically equivalent structure,
the comparison can continue into deeper registered layers.

## Return failures as tokens

When your engine fails, capture the failure in the returned `ValidationToken`
instead of raising from `execute()`. The snippet below is intentionally partial:
it shows only the error-handling branch.

If execution fails, return a token with an error status instead of raising:

```python
def execute(self, task: EleguaTask) -> ValidationToken:
    try:
        result = my_engine.run(task.action, task.payload)
        return ValidationToken(
            adapter_id=self.adapter_id,
            status=TaskStatus.OK,
            result=result,
        )
    except MyEngineError as e:
        return ValidationToken(
            adapter_id=self.adapter_id,
            status=TaskStatus.EXECUTION_ERROR,
            metadata={"error": str(e)},
        )
```

## Common fail-state: no lifecycle setup

If your adapter uses `initialize()` or `teardown()`, run it as a context
manager. Calling `execute()` before setup is a common mistake for adapters that
manage external connections or processes.

```python
adapter = MyAdapter()
token = adapter.execute(task)  # safe only for adapters with no initialize() work
```

For adapters that open network clients, kernels, or temporary state, prefer:

```python
with MyAdapter() as adapter:
    token = adapter.execute(task)
```

For adapters backed by an HTTP oracle server, see [Oracle servers](oracle-servers.md).
