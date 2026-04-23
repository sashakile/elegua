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

## Execution model at a glance

```
TOML fixture → EleguaTask → Adapter.execute() → ValidationToken → Comparison Pipeline → pass/fail
```

## Choose your path

Based on your goal, consider the following entry points:

### 1. Evaluate Eleguá
If you want to run a quick test using the built-in stubs:
- [Getting started](getting-started.md) — install and run your first comparison
- [Architecture](architecture.md) — understand the three-tier model

### 2. Build an adapter
If you want to connect Eleguá to your own symbolic engine:
- [Task lifecycle](guide/tasks.md)
- [Writing an adapter](guide/adapters.md)
- [Comparison pipeline](guide/comparison.md)

### 3. Contribute
If you want to help develop the Eleguá core harness:
- [Development](development.md) — set up the local contributor environment
- [API reference](reference/) — auto-generated from source

The remaining guide pages ([TOML format](guide/toml-format.md), [Property testing](guide/property-testing.md), [Blob store](guide/blob-store.md), [Oracle servers](guide/oracle-servers.md)) can be read in any order as needed.
