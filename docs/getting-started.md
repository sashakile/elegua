# Getting started

## Prerequisites

You need the following installed:

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/) — Python package manager
- [just](https://just.systems/) — command runner
- [typos](https://github.com/crate-ci/typos) — spell checker
- [vale](https://vale.sh/) — prose linter

## Installation

```bash
git clone git@github.com:sashakile/elegua.git
cd elegua
just setup
```

This installs all dependencies, syncs vale styles, and configures git hooks.

## Verify the setup

```bash
just check    # lint, format, typecheck, typos, vale
just test     # 88 tests, 100% coverage
```

## Run your first test

Create a TOML test file:

```toml
[meta]
name = "simple round-trip"

[[tasks]]
action = "MyAction"
[tasks.payload]
input = "hello"
```

Load and run it from Python:

```python
from pathlib import Path
from elegua.runner import load_toml_tasks, run_tasks

tasks = load_toml_tasks(Path("my_test.toml"))
tokens = run_tasks(tasks)

for token in tokens:
    print(f"{token.adapter_id}: {token.status}")
```

## Compare results across adapters

```python
from pathlib import Path
from elegua.adapter import WolframAdapter
from elegua.comparison import compare_pipeline
from elegua.runner import load_toml_tasks, run_tasks

tasks = load_toml_tasks(Path("my_test.toml"))

oracle_tokens = run_tasks(tasks, adapter=WolframAdapter())
iut_tokens = run_tasks(tasks, adapter=WolframAdapter())  # replace with your adapter

for oracle, iut in zip(oracle_tokens, iut_tokens, strict=True):
    result = compare_pipeline(oracle, iut)
    print(f"Layer {result.layer}: {result.status}")
```
