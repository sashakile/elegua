# Architecture

**Eleguá's three-tier model and 4-layer pipeline prove that two symbolic math implementations produce equivalent results.**

> **What it does** — Three tiers (Oracle, literal port, idiomatic target) run the same operations. A 4-layer comparison pipeline (identity → structural → canonical → invariant) finds the cheapest match.  
> **Use this when** — You want to understand how Eleguá works before writing adapters or fixtures.  
> **Prerequisites** — [Getting started](getting-started.md).  
> **Outcome** — Understand the execution model, pipeline layers, and design principles.

Eleguá's architecture solves a specific problem: when porting a symbolic math library across languages, you need to prove that the port produces equivalent results to the original — not just for simple cases, but for the full space of symbolic expressions.

## Three-tier execution model

Eleguá validates mathematical systems by comparing results across tiers of decreasing fidelity.

| Tier | Role | Example |
|------|------|---------|
| **Tier 1** | High-fidelity Oracle (ground truth) | Wolfram xAct |
| **Tier 2** | Literal port | xAct-jl |
| **Tier 3** | Idiomatic target | Chacana-jl |

Each tier implements the `Adapter` interface. The orchestrator sends the same `EleguaTask` to multiple adapters and compares the resulting `ValidationToken` objects.

## Data flow

```
┌──────────┐     ┌─────────────┐     ┌───────────────┐     ┌────────────┐
│ TOML     │────▶│ EleguaTask  │────▶│ Adapter       │────▶│ Validation │
│ Fixture  │     │ (action +   │     │ .execute()    │     │ Token      │
│          │     │  payload)   │     │               │     │            │
└──────────┘     └─────────────┘     └───────────────┘     └────────────┘
                                                                  │
                                                                  ▼
                                                          ┌────────────┐
                                                          │ Comparison │
                                                          │ Pipeline   │
                                                          │ (4 layers) │
                                                          └────────────┘
```

## 4-layer comparison pipeline

The pipeline cascades through layers, stopping at the first that confirms equivalence.

| Layer | Method | Goal | Success criteria |
|-------|--------|------|------------------|
| **1. Identity** | Structural equality | Instant validation | `result_a == result_b` |
| **2. Structural** | Sorted canonical form | AST isomorphism | `canonical(a) == canonical(b)` |
| **3. Canonical** | Normalizer rules | Semantic equivalence | `normalize(a) == normalize(b)` |
| **4. Invariant** | Numeric sampling / domain checks | Mathematical evidence | `f(a, args) ≈ f(b, args)` |

Layers 1-2 are implemented in the core. Layers 3-4 are domain-specific extension points.

!!! note "Known limitation"
    Layer 2 treats all list orderings as equivalent via sorted canonical form. This means non-commutative operations (like subtraction) may produce false positives. Layers 3-4 catch these cases when domain-specific normalizers are registered.

## Eleguá design principles

- **Domain-agnostic core** — the orchestrator has no knowledge of tensor calculus, integration rules, or any specific mathematical domain
- **Immutability** — `Adapter.execute()` returns a new `ValidationToken` and must not mutate the input task
- **State machine enforcement** — task transitions are validated; invalid transitions raise exceptions
- **Isolation** — each adapter execution must be independent to prevent state leakage between tests
