# Writing an adapter

Adapters connect Eleguá to external symbolic engines. Each adapter translates an `EleguaTask` into a call to its engine and returns a `ValidationToken` with the result.

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

## Using your adapter

Pass it to `run_tasks()`:

```python
from elegua.runner import load_toml_tasks, run_tasks

tasks = load_toml_tasks(Path("my_test.toml"))
tokens = run_tasks(tasks, adapter=MyAdapter())
```

## Error handling

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

## Multi-tier comparison

To compare Oracle and IUT results, run the same tasks through both adapters:

```python
from elegua.comparison import compare_pipeline

oracle_tokens = run_tasks(tasks, adapter=WolframAdapter())
iut_tokens = run_tasks(tasks, adapter=MyAdapter())

for oracle, iut in zip(oracle_tokens, iut_tokens, strict=True):
    result = compare_pipeline(oracle, iut)
    print(f"Layer {result.layer}: {result.status}")
```
