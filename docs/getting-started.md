# Getting started

**Install Eleguá and run your first comparison in under five minutes.**

> **What it does** — Install Eleguá, load a TOML fixture, run it through an adapter, and compare two results in under five minutes.  
> **Use this when** — You're new to Eleguá and want to see it work end-to-end.  
> **Prerequisites** — Python 3.11+, `uv`.  
> **Outcome** — A working installation and a passing comparison verdict.

This guide walks you through installing Eleguá and running a complete validation — from TOML fixture to comparison verdict.

## Prerequisites

You need the following installed:

- **Python 3.11 or later** — [python.org/downloads](https://www.python.org/downloads/)
- **uv** — `curl -LsSf https://astral.sh/uv/install.sh | sh` ([docs](https://docs.astral.sh/uv/))

## Install the package

```bash
git clone https://github.com/sashakile/elegua.git  # or git@github.com:sashakile/elegua.git
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

The repository ships with a test fixture at `tests/fixtures/sxact_basic.toml`:

```toml
[meta]
id              = "bridge/basic"
description     = "Bridge loader smoke test"
tags            = ["bridge", "layer:1"]
layer           = 1
oracle_is_axiom = true

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

Each test file declares a **meta** section, optional **setup** operations, and named **tests** with operations and optional expected outcomes.

### Step 1 — Load and run a fixture

```python
from pathlib import Path
from elegua.bridge import load_test_file
from elegua.adapter import WolframAdapter
from elegua.isolation import IsolatedRunner

test_file = load_test_file(Path("tests/fixtures/sxact_basic.toml"))

with IsolatedRunner(WolframAdapter()) as runner:
    results = runner.run(test_file)

for r in results:
    status = "skipped" if r.skipped else "ok" if not r.error else "error"
    print(f"{r.test_id}: {status}")
```

```text
canon_symmetric: ok
registry_check: ok
```

### Step 2 — Compare oracle vs IUT

```python
from elegua.multitier import MultiTierRunner
from elegua.comparison import ComparisonPipeline

pipeline = ComparisonPipeline()

with MultiTierRunner(WolframAdapter(), WolframAdapter(), pipeline=pipeline) as runner:
    results = runner.verify(test_file)

for vr in results:
    status = vr.comparison.status.value
    print(f"{vr.test_id}: {status}")
```

```text
canon_symmetric: ok
registry_check: ok
```

`MultiTierRunner` runs the same fixture through two different adapters and compares their outputs using the 4-layer `ComparisonPipeline`. When both adapters agree, the result is `ok`. When they diverge, the pipeline identifies which layer detected the mismatch and provides diagnostics.

!!! tip "Legacy format"
    Older fixtures like `tests/fixtures/tracer.toml` use a flat `[[tasks]]` format. The `elegua run` CLI command (\u2014oracle \u2014iut) handles both formats transparently.

!!! note "The WolframAdapter is a stub"
    The built-in `WolframAdapter` echoes the input payload as its result. It exists to prove the architecture works end-to-end. Replace it with a real adapter that connects to your symbolic engine \u2014 see [Writing an adapter](guide/adapters.md).

## Next steps

- [Task lifecycle](guide/tasks.md) — understand `EleguaTask`, `ValidationToken`, and state transitions
- [Writing an adapter](guide/adapters.md) — connect Eleguá to your own symbolic engine
- [Comparison pipeline](guide/comparison.md) — how the 4-layer cascade works

## Summary

You have installed Eleguá, loaded a TOML fixture, run it through an adapter, and compared two runs using the multi-tier runner. This is the core workflow: declare operations in TOML, execute them through adapters, and compare results.