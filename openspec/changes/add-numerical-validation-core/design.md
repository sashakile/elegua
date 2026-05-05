## Context
Eleguá is a domain-agnostic multi-tier validation harness. Its current core already supports adapter execution, TOML fixtures, a four-layer comparison pipeline, property-based tests, and SHA-256 blob storage. Numerical users need common semantics that are not finance-specific: tolerance composition, stochastic comparison, array handling, capability negotiation, differential relations, convergence rates, longitudinal provenance, and efficient warm adapter execution.

## Goals / Non-Goals
- Goals:
  - Provide reusable numerical-validation primitives in core without assuming a domain such as finance.
  - Preserve existing symbolic workflows and comparison behavior by making new features opt-in or additive.
  - Make numerical failures diagnosable through structured verdicts, provenance, top-K disagreements, and history queries.
  - Reduce wall-clock time for expensive adapters while preserving isolation through explicit reset semantics.
- Non-Goals:
  - Do not add finance-specific profiles, conventions, arbitrage rules, or day-count corpora to core.
  - Do not turn Eleguá into a performance benchmarking framework, workflow scheduler, IDE integration, or language-native static-analysis replacement.
  - Do not require every adapter to implement numerical metadata or every fixture to declare capabilities.

## Decisions
- Decision: Introduce a new numeric layer after canonical comparison and before invariant comparison.
  - Rationale: Numeric comparison is more general than domain invariants and should be reusable before falling back to plugin-specific logic.
  - Alternatives considered: Keep all numeric behavior in Layer 4 plugins; rejected because every numerical domain would duplicate tolerance, stochastic, and array logic.
- Decision: Store numeric payload information in token metadata/result conventions rather than changing `ValidationToken`'s core shape immediately.
  - Rationale: Maintains compatibility with current adapters while allowing typed helper models and validation at comparison time.
- Decision: Use an open string capability vocabulary with optional structured metadata.
  - Rationale: Core can ship baseline capabilities while plugins extend namespaces without central coordination.
- Decision: Model differential and convergence checks as fixture types that produce normal tokens/verdicts.
  - Rationale: They participate in existing comparison, blob, provenance, and reporting machinery rather than becoming separate test systems.
- Decision: Ship both local and CI-oriented history backends behind a common interface.
  - Rationale: SQLite is simplest locally; DuckDB/Parquet scales for CI and analytics.
- Decision: Connection pooling must be opt-in via adapter lifecycle declarations and bounded by adapter-specific pool sizes.
  - Rationale: Isolation remains the default; expensive adapters can reuse process/kernel state only when they can reset safely.

## Risks / Trade-offs
- Numeric defaults may be misused as domain truth → Mitigation: ship conservative generic defaults, require profile versioning, document domain-specific profile ownership.
- Capability vocabulary may sprawl → Mitigation: document standard names and namespace guidance for plugin-owned capabilities.
- Relation plugins can become arbitrary bespoke logic → Mitigation: keep plugin interface small and document that complex workflows should remain regular fixtures or domain plugins.
- Provenance schema migration is a long-term commitment → Mitigation: schema versioning, append-only evolution, and documented retention/migration policies.
- Adapter reset bugs can leak state → Mitigation: provide `verify_isolation` helper and default pool size of 1 / fresh instances for cheap adapters.

## Migration Plan
1. Add helper data models and registry APIs behind existing public interfaces.
2. Implement each feature behind opt-in fixture declarations or CLI flags.
3. Keep current fixture schemas, adapter lifecycle hooks, blob APIs, and comparison short-circuit behavior working.
4. Add docs, examples, and compatibility tests before enabling any new defaults.
5. Defer finance-specific work to a separate plugin proposal after the core primitives are approved.

## Open Questions
- Should the history store default to SQLite only, or install DuckDB support by default as an optional dependency?
- Should tolerance profile names be flat (`numerical_default`) or hierarchical (`core/numerical_default`)?
- What minimum environment fingerprint is stable enough for provenance hashes across platforms?
- Should fixture matrix expansion be eager initially, with lazy expansion reserved for a future change?
