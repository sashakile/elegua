# Eleguá

**Domain-agnostic, multi-tier test harness for validating mathematical equivalence.**

Eleguá proves that two implementations of the same mathematical system produce equivalent results. It runs identical symbolic actions on a high-fidelity Oracle and one or more Implementations Under Test (IUT), then compares outputs through a 4-layer pipeline — from fast structural equality to deeper semantic and invariant-based checks — stopping at the first layer that confirms a match.

In short, define test cases in TOML, write an Adapter for each implementation, and let Eleguá tell you whether they agree — and at what level of analysis.

## Key features

- **Multi-tier execution** — validate results across Oracle and IUT implementations
- **4-layer comparison pipeline** — progressive refinement from identity to semantic and invariant-based comparison
- **TOML-based test definitions** — declarative, language-agnostic test specs
- **Property-based testing utilities** — Hypothesis-based law checks alongside the comparison pipeline
- **SHA-256 blob store** — transparent handling of large symbolic expressions
- **State machine enforcement** — validated task lifecycle transitions

## Try the package locally

```bash
git clone git@github.com:sashakile/elegua.git
cd elegua
uv sync
uv run python -c 'from elegua.adapter import WolframAdapter; from elegua.comparison import compare_pipeline; from elegua.task import EleguaTask; task = EleguaTask(action="Echo", payload={"expr": "x + y"}); a = WolframAdapter().execute(task); b = WolframAdapter().execute(task); result = compare_pipeline(a, b); print(result.layer, result.layer_name, result.status.value)'
```

## Execution model at a glance

```
TOML fixture → EleguaTask → Adapter.execute() → ValidationToken → Comparison Pipeline → pass/fail
```

1. Load test definitions from TOML files
2. Instantiate `EleguaTask` objects with action and payload
3. Execute through one or more `Adapter` implementations
4. Compare `ValidationToken` results through the 4-layer pipeline
5. Report pass/fail with the layer that resolved equivalence

## Read next

- [Getting started](getting-started.md) — install prerequisites and run your first comparison
- [Architecture](architecture.md) — understand the three-tier model and design decisions
- [User guide](guide/tasks.md) — work with tasks, adapters, and comparison layers
- [API reference](reference/) — auto-generated from source
