# TOML test format

**Define test cases and property specs in TOML so your validation suite is declarative and language-agnostic.**

Task files describe actions to execute; property files describe mathematical laws to validate by sampling.

## Task files

Task files define a sequence of actions to execute through an adapter.

```toml
[meta]
name = "DefTensor+Contract round-trip"
description = "Define a rank-2 tensor and contract it"

[[tasks]]
action = "DefTensor"
[tasks.payload]
name = "T"
indices = ["a", "b"]

[[tasks]]
action = "Contract"
[tasks.payload]
expr = "T[a, b] * g[-a, -b]"
```

### Structure

- `[meta]` — optional metadata (name, description)
- `[[tasks]]` — one or more task entries, each with:
    - `action` (required) — the operation name
    - `[tasks.payload]` (optional) — key-value pairs passed to the adapter

### Loading

```python
from pathlib import Path
from elegua.runner import load_toml_tasks

tasks = load_toml_tasks(Path("tests/fixtures/tracer.toml"))
for task in tasks:
    print(f"{task.action}: {task.payload}")
```

### Validation

- Missing `tasks` key raises `SchemaError`
- Missing `action` field on any task raises `SchemaError` with the task index
- Empty `action` string is treated as missing

`SchemaError` is a subclass of both `EleguaError` and `ValueError`, so `except ValueError` catches it too.

## Property files

Property files define mathematical laws to validate via sampling. See [property testing](property-testing.md) for the full format.

```toml
name = "negate_involution"
layer = "property"
law = "f(f($x)) == $x"

[[generators]]
name = "$x"
type = "integer"
```
