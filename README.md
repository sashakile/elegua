# Eleguá

Domain-agnostic, multi-tier test harness for validating mathematical equivalence across symbolic computing systems.

## What it does

Eleguá orchestrates validation tasks across multiple implementations of the same mathematical system. It proves functional equivalence by running the same symbolic action on a high-fidelity Oracle and one or more Implementations Under Test, then comparing results through a multi-layer pipeline.

**Three-tier execution model:**

| Tier | Role | Example |
|------|------|---------|
| Tier 1 | High-fidelity Oracle (ground truth) | Wolfram xAct |
| Tier 2 | Literal port | xAct-jl |
| Tier 3 | Idiomatic target | Chacana-jl |

**4-layer comparison pipeline:**

1. **Identity** — structural equality of result payloads
2. **Structural** — AST isomorphism via sorted canonical form
3. **Canonical** — pluggable normalizer rules (domain-specific)
4. **Invariant** — numerical sampling and property-based testing (domain-specific)

The pipeline cascades: it stops at the first layer that confirms equivalence.

## Architecture

```
TOML fixture → EleguaTask → Adapter.execute() → ValidationToken → Comparison Pipeline → pass/fail
```

**Core modules:**

| Module | Purpose |
|--------|---------|
| `task.py` | `EleguaTask` model, `TaskStatus` enum, state machine with validated transitions |
| `models.py` | `ActionPayload` (adapter input) and `ValidationToken` (adapter output) |
| `adapter.py` | `Adapter` ABC and `WolframAdapter` stub |
| `comparison.py` | 4-layer comparison pipeline with `ComparisonResult` |
| `runner.py` | TOML test loader and parameterized task executor |
| `blobstore.py` | SHA-256 content-addressed store for payloads exceeding 1 MB |
| `property.py` | Property-based test runner with PCG64 seed-based reproducibility |

## Getting started

You need Python 3.11+, [uv](https://docs.astral.sh/uv/), [just](https://just.systems/), [typos](https://github.com/crate-ci/typos), and [vale](https://vale.sh/).

```bash
git clone git@github.com:sashakile/elegua.git
cd elegua
just setup    # installs deps, syncs vale styles, configures git hooks
```

Verify everything works:

```bash
just check    # lint, format, typecheck, typos, vale
just test     # 88 tests, 100% coverage
```

## Development

```bash
just setup      # one-time: install deps + git hooks
just check      # run all pre-commit checks
just fix        # auto-fix lint and format issues
just test       # run tests (pass args: just test -v -k blob)
just cov        # tests with coverage report
just ci         # full local CI: check + test
just lint       # ruff lint only
just fmt        # ruff format only
just typecheck  # pyright only
```

**Git hooks** (installed by `just setup`):

- **pre-commit**: ruff check, ruff format, pyright, typos, vale
- **pre-push**: pytest

**CI** runs on push and PR to main: lint, typecheck, typos, vale, and test matrix across Python 3.11-3.13.

## Task lifecycle

```
PENDING → RUNNING → OK | MATH_MISMATCH | EXECUTION_ERROR | TIMEOUT
```

State transitions are enforced by `EleguaTask.transition()`. Invalid transitions raise `InvalidTransition`. The method returns a new task (no mutation).

## TOML test format

```toml
[meta]
name = "DefTensor+Contract round-trip"

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

## Property-based testing

Property specs use TOML with PCG64-seeded sampling for cross-platform reproducibility:

```toml
name = "negate_involution"
layer = "property"
law = "f(f($x)) == $x"

[[generators]]
name = "$x"
type = "integer"
```

Register domain-specific generators via `GeneratorRegistry`, then run with `PropertyRunner`.

## Blob store

Payloads exceeding 1 MB are stored by SHA-256 hash in a two-level directory: `.elegua/blobs/ab/cd...`. Use `BlobStore.maybe_store()` and `BlobStore.maybe_resolve()` for transparent handling.

## License

See LICENSE file.
