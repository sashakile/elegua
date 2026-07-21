# TOML test format

**Define test cases and property specs in TOML so your validation suite is declarative and language-agnostic.**

> **What it does** — Task files (`.toml`) define operations to execute through adapters. Property files define mathematical laws for Hypothesis-based sampling. Both are declarative and language-agnostic.  
> **Use this when** — You're writing test fixtures or property specs for your validation suite.  
> **Prerequisites** — [Getting started](../getting-started.md) for the overall workflow.  
> **Outcome** — Know the TOML task file structure, property file structure, and loading/validation mechanics.

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
from elegua.bridge import load_test_file

test_file = load_test_file(Path("tests/fixtures/sxact_basic.toml"))
for test in test_file.tests:
    for op in test.operations:
        print(f"{op.action}: {op.args}")
```

### Validation

- Missing `meta` key raises `SchemaError`
- Missing `id` or `description` in `[meta]` raises `SchemaError`
- Missing `action` field on any operation raises `SchemaError`
- Empty `action` string is treated as missing

`SchemaError` is a subclass of both `EleguaError` and `ValueError`, so `except ValueError` catches it too.

!!! tip "Legacy format"
    Older task files like `tests/fixtures/tracer.toml` use a flat `[[tasks]]` format without setup or named tests.
    The `elegua run` CLI command and `load_test_file()` both support the legacy format.

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
