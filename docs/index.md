# Eleguá

**Domain-agnostic, multi-tier test harness for validating mathematical equivalence.**

Eleguá proves that two implementations of the same mathematical system produce equivalent results. It runs identical symbolic actions on a high-fidelity Oracle and one or more Implementations Under Test (IUT), then compares outputs through a 4-layer pipeline — from fast structural equality to deep property-based testing — stopping at the first layer that confirms a match.

In short, define test cases in TOML, write an Adapter for each implementation, and let Eleguá tell you whether they agree — and at what level of analysis.

## Key features

- **Multi-tier execution** — validate results across Oracle and IUT implementations
- **4-layer comparison pipeline** — progressive refinement from bitwise identity to property-based testing
- **TOML-based test definitions** — declarative, language-agnostic test specs
- **Property-based testing** — reproducible sampling with PCG64 seeds
- **SHA-256 blob store** — transparent handling of large symbolic expressions
- **State machine enforcement** — validated task lifecycle transitions

## Quick start

```bash
git clone git@github.com:sashakile/elegua.git
cd elegua
just setup
just test
```

## How it works

```
TOML fixture → EleguaTask → Adapter.execute() → ValidationToken → Comparison Pipeline → pass/fail
```

1. Load test definitions from TOML files
2. Instantiate `EleguaTask` objects with action and payload
3. Execute through one or more `Adapter` implementations
4. Compare `ValidationToken` results through the 4-layer pipeline
5. Report pass/fail with the layer that resolved equivalence

## Next steps

- [Getting started](getting-started.md) — install prerequisites and run your first comparison
- [Architecture](architecture.md) — understand the three-tier model and design decisions
- [User guide](guide/tasks.md) — work with tasks, adapters, and comparison layers
- [API reference](reference/) — auto-generated from source
