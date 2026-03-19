# Getting started

This guide walks you through installing Eleguá and running a complete validation — from TOML fixture to comparison verdict.

## Prerequisites

You need the following installed:

- **Python 3.11 or later** — [python.org/downloads](https://www.python.org/downloads/)
- **uv** — `curl -LsSf https://astral.sh/uv/install.sh | sh` ([docs](https://docs.astral.sh/uv/))
- **just** — `cargo install just` or `brew install just` ([docs](https://just.systems/))
- **typos** — `cargo install typos-cli` or `brew install typos-cli` ([repository](https://github.com/crate-ci/typos))
- **vale** — `brew install vale` or download from [vale.sh/docs/install](https://vale.sh/docs/install/) ([docs](https://vale.sh/))

!!! tip "Don't have Cargo?"
    If you don't have Rust/Cargo installed, use `brew install just typos-cli` on macOS, or check each tool's install page for binary downloads.

## Installation

```bash
git clone git@github.com:sashakile/elegua.git
cd elegua
just setup
```

This installs all Python dependencies, syncs vale styles, and configures git hooks.

!!! note "If `just setup` fails"
    The most common cause is a missing prerequisite. Run `just setup` again after installing any missing tool — it is idempotent.

## Verify the setup

```bash
just check    # lint, format, typecheck, typos, vale
just test     # full test suite with 100% coverage
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

Load the fixture, execute it through two adapters, and compare the results:

```python
from pathlib import Path

from elegua.adapter import WolframAdapter
from elegua.comparison import ComparisonPipeline
from elegua.runner import load_toml_tasks, run_tasks

# 1. Load tasks from the TOML fixture
tasks = load_toml_tasks(Path("tests/fixtures/tracer.toml"))

# 2. Execute through two adapters (both use the WolframAdapter stub for now)
oracle_tokens = run_tasks(tasks, adapter=WolframAdapter())
iut_tokens = run_tasks(tasks, adapter=WolframAdapter())

# 3. Compare each pair through the 4-layer pipeline
pipeline = ComparisonPipeline()
for oracle, iut in zip(oracle_tokens, iut_tokens, strict=True):
    result = pipeline.compare(oracle, iut)
    print(f"{oracle.adapter_id} vs {iut.adapter_id}: "
          f"layer {result.layer} ({result.layer_name}) → {result.status.value}")
```

Expected output:

```
wolfram vs wolfram: layer 1 (identity) → ok
wolfram vs wolfram: layer 1 (identity) → ok
```

Both tasks match at layer 1 (identity) because the same adapter produces identical output. When you swap in a real IUT adapter, mismatches cascade through deeper layers — structural, canonical, and property-based — until equivalence is confirmed or a mismatch is reported.

!!! note "The WolframAdapter is a stub"
    The built-in `WolframAdapter` echoes the input payload as its result. It exists to prove the architecture works end-to-end. Replace it with a real adapter that connects to your symbolic engine — see [Writing an adapter](guide/adapters.md).

## Next steps

- [Task lifecycle](guide/tasks.md) — understand `EleguaTask`, `ValidationToken`, and state transitions
- [Writing an adapter](guide/adapters.md) — connect Eleguá to your own symbolic engine
- [Comparison pipeline](guide/comparison.md) — how the 4-layer cascade works
- [Architecture](architecture.md) — the three-tier model and design principles
