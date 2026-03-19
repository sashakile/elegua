# Eleguá

Domain-agnostic, multi-tier test harness for validating mathematical equivalence across symbolic computing systems.

## The problem

When you port a symbolic math library to a new language, how do you prove the new implementation produces the same results as the original? Manual spot-checks don't scale — you need automated, layer-by-layer comparison that catches everything from bitwise differences to deep semantic mismatches.

## What Eleguá does

Eleguá orchestrates validation tasks across multiple implementations of the same mathematical system. It runs the same symbolic action on a high-fidelity Oracle (ground truth) and one or more Implementations Under Test, then compares results through a 4-layer pipeline that cascades from fast structural checks to deep property-based testing.

```
TOML fixture → EleguaTask → Adapter.execute() → ValidationToken → Comparison Pipeline → pass/fail
```

## Getting started

### Prerequisites

- **Python 3.11+** — [python.org/downloads](https://www.python.org/downloads/)
- **uv** — `curl -LsSf https://astral.sh/uv/install.sh | sh` ([docs](https://docs.astral.sh/uv/))
- **just** — `cargo install just` or `brew install just` ([docs](https://just.systems/))
- **typos** — `cargo install typos-cli` or `brew install typos-cli` ([repository](https://github.com/crate-ci/typos))
- **vale** — `brew install vale` or download from [vale.sh/docs/install](https://vale.sh/docs/install/) ([docs](https://vale.sh/))

### Install and verify

```bash
git clone git@github.com:sashakile/elegua.git
cd elegua
just setup    # installs deps, syncs vale styles, configures git hooks
just check    # lint, format, typecheck, typos, vale
just test     # full test suite with 100% coverage
```

See the [full documentation](https://sashakile.github.io/elegua/) for the user guide, architecture overview, and API reference.

## Development

```bash
just setup      # one-time: install deps + git hooks
just check      # run all pre-commit checks
just fix        # auto-fix lint and format issues
just test       # run tests (pass args: just test -v -k blob)
just cov        # tests with coverage report
just ci         # full local CI: check + test
```

**Git hooks** (installed by `just setup`): pre-commit runs ruff, pyright, typos, and vale; pre-push runs pytest.

**CI** runs on push and PR to main: lint, typecheck, typos, vale, and test matrix across Python 3.11–3.13.

## License

MIT
