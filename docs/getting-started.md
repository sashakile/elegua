# Getting started

**Install Eleguá and run your first comparison in under five minutes.**

This guide walks you through installing Eleguá and running a complete validation — from TOML fixture to comparison verdict.

## Minimal prerequisites

You need the following installed:

- **Python 3.11 or later** — [python.org/downloads](https://www.python.org/downloads/)
- **uv** — `curl -LsSf https://astral.sh/uv/install.sh | sh` ([docs](https://docs.astral.sh/uv/))

## Install the package

```bash
git clone git@github.com:sashakile/elegua.git
cd elegua
uv sync
```

This installs the package and its Python dependencies for local use.

## Optional contributor tooling

If you plan to work on the repository itself, install the contributor tools used
by the local checks and git hooks:

- **just** — `cargo install just` or `brew install just` ([docs](https://just.systems/))
- **typos** — `cargo install typos-cli` or `brew install typos-cli` ([repository](https://github.com/crate-ci/typos))
- **vale** — `brew install vale` or download from [vale.sh/docs/install](https://vale.sh/docs/install/) ([docs](https://vale.sh/))

Then run:

```bash
just setup    # install deps, sync vale, configure hooks
just check    # run all pre-commit checks
just test     # run tests
just cov      # run tests with coverage report
```

## Run your first comparison

The repository ships with a test fixture at `tests/fixtures/tracer.toml`:

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

### Step 1 — Load tasks from TOML

```python
from pathlib import Path
from elegua.runner import load_toml_tasks

tasks = load_toml_tasks(Path("tests/fixtures/tracer.toml"))
for task in tasks:
    print(f"{task.action}: {task.payload}")
```

```text
DefTensor: {'name': 'T', 'indices': ['a', 'b']}
Contract: {'expr': 'T[a, b] * g[-a, -b]'}
```

### Step 2 — Execute through an adapter

```python
from elegua.adapter import WolframAdapter
from elegua.runner import run_tasks

oracle_tokens = run_tasks(tasks, adapter=WolframAdapter())
for token in oracle_tokens:
    print(f"{token.adapter_id}: {token.status.value} → {token.result}")
```

```text
wolfram: ok → {'name': 'T', 'indices': ['a', 'b']}
wolfram: ok → {'expr': 'T[a, b] * g[-a, -b]'}
```

### Step 3 — Compare two runs

```python
from elegua.comparison import compare_pipeline

iut_tokens = run_tasks(tasks, adapter=WolframAdapter())
for oracle, iut in zip(oracle_tokens, iut_tokens, strict=True):
    result = compare_pipeline(oracle, iut)
    print(f"layer {result.layer} ({result.layer_name}) → {result.status.value}")
```

```text
layer 1 (identity) → ok
layer 1 (identity) → ok
```

Both tasks match at layer 1 (identity) because the same adapter produces identical output. `compare_pipeline()` runs the default L1+L2 layers. When you need custom layers (L3/L4), instantiate a `ComparisonPipeline` directly — see [Comparison pipeline](guide/comparison.md).

!!! note "The WolframAdapter is a stub"
    The built-in `WolframAdapter` echoes the input payload as its result. It exists to prove the architecture works end-to-end. Replace it with a real adapter that connects to your symbolic engine — see [Writing an adapter](guide/adapters.md).

## Next steps

- [Task lifecycle](guide/tasks.md) — understand `EleguaTask`, `ValidationToken`, and state transitions
- [Writing an adapter](guide/adapters.md) — connect Eleguá to your own symbolic engine
- [Comparison pipeline](guide/comparison.md) — how the 4-layer cascade works
- [Blob store](guide/blob-store.md) — automatic handling of large payloads (> 1 MB)
- [Architecture](architecture.md) — the three-tier model and design principles
