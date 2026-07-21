# TOML test format

**Read this page when you're writing test fixtures or property specs — it covers the TOML structure for both task files and property files.**

> **What it does** — Task files (`.toml`) define operations to execute through adapters. Property files define mathematical laws for Hypothesis-based sampling. Both are declarative and language-agnostic.  
> **Use this when** — You're writing test fixtures or property specs for your validation suite.  
> **Prerequisites** — [Getting started](../getting-started.md) for the overall workflow.  
> **Outcome** — Know the TOML task file structure, property file structure, and loading/validation mechanics.

## Task files

Task files define a sequence of operations to execute through an adapter. Each file can declare setup operations and one or more named tests.

```toml
[meta]
id          = "bridge/basic"
description = "Bridge loader smoke test"

[[setup]]
action   = "DefManifold"
store_as = "M"
[setup.args]
name      = "M"
dimension = 4
indices   = ["a", "b", "c", "d"]

[[tests]]
id          = "canon_symmetric"
description = "Symmetric swap canonicalizes to zero"

[[tests.operations]]
action   = "Evaluate"
store_as = "diff"
[tests.operations.args]
expression = "T[-a,-b] - T[-b,-a]"
```

### Task file structure

- `[meta]` — required metadata (id, description)
- `[[setup]]` — optional setup operations, run before any test
- `[[tests]]` — one or more named test blocks, each with:
    - `id` (required) — unique test identifier
    - `[[tests.operations]]` — one or more operations, each with:
        - `action` (required) — the operation name
        - `[tests.operations.args]` (optional) — key-value pairs passed to the adapter

### Loading task files

```python
from pathlib import Path
from elegua.bridge import load_test_file

test_file = load_test_file(Path("tests/fixtures/sxact_basic.toml"))
for test in test_file.tests:
    for op in test.operations:
        print(f"{op.action}: {op.args}")
```

### Schema validation

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
