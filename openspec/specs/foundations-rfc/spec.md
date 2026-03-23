# Specification: Eleguá and Chacana Foundations RFC

## Metadata
- **Change-ID**: `REQ-FOUND-001`
- **Version**: `1.3.0`
- **Status**: `IMPLEMENTED`
- **Last Updated**: 2026-03-19

## Purpose
This RFC defines the architectural pivot to decouple the `sxAct` project into two primary pillars: **Eleguá** (The Orchestrator) and **Chacana** (The Language). It establishes the three-tier execution strategy and the use of a common intermediate representation (CIR) for universal symbolic interchange.

## Requirements

### Requirement: Decoupling of DSL and Harness
The system SHALL separate the tensor calculus DSL (Chacana) from the test orchestration harness (Eleguá) via a standard Adapter Interface.

#### Scenario: Reuse Eleguá for different domains
- **GIVEN** a new symbolic domain like RUBI is implemented
- **WHEN** the RUBI adapter is registered with Eleguá
- **THEN** it MUST be possible to execute RUBI verification tasks using the same Eleguá orchestrator.

#### Scenario: Negative - Invalid Adapter Implementation
- **GIVEN** an adapter that does not implement the required `execute` method
- **WHEN** it is instantiated
- **THEN** Python's ABC enforcement MUST raise a `TypeError` preventing instantiation.

### Requirement: Three-Tier Verification
The system SHALL support verification across three distinct execution tiers to prove mathematical equivalence.

#### Scenario: Verify Tier 3 against Tier 1
- **GIVEN** a task manifest defining Tier 1 (Wolfram) and Tier 3 (Chacana-jl)
- **WHEN** a result from the Chacana-jl engine (Tier 3) is compared
- **THEN** it MUST be verified against the Wolfram xAct "Gold Standard" (Tier 1).

#### Scenario: Negative - Tier Initialization Failure
- **GIVEN** a manifest requiring 3 tiers
- **WHEN** one tier fails to initialize
- **THEN** the orchestrator MUST return an `EXECUTION_ERROR` for that tier and continue with remaining tiers if configured.

## Design Details

### 1. The Three-Tier Strategy
- **Tier 1 (Wolfram xAct v1.1.2)**: The Gold Standard Oracle.
- **Tier 2 (xAct-jl)**: Literal Julia port for high-speed local verification.
- **Tier 3 (Chacana-jl)**: Idiomatic, high-performance Julia using `Symbolics.jl`.

### 2. Common Intermediate Representation (CIR)
Adapters return results as plain dict payloads within `ValidationToken`. The format is domain-specific — Eleguá's comparison pipeline operates on structural equality, sorted canonical form, and pluggable normalizers without requiring a fixed AST schema.

### 3. Extension Model
Domain-specific oracle servers are shipped as optional extras rather than built into the core. This preserves domain-agnosticism while providing ready-made integrations:

- `pip install elegua[wolfram]` — Wolfram kernel oracle server with configurable init scripts and cleanup expressions. Downstream projects (e.g., sxAct) inject domain-specific setup via environment variables.
- Future extras follow the same pattern for Julia, Sage, or other CAS engines.

### 4. Implementation Roadmap
- **Phase 1: Eleguá Core**: Generalization of the runner into a domain-agnostic orchestrator. **IMPLEMENTED** (v0.1.0, 2026-03-19). Includes: task state machine, 4-layer comparison pipeline (L1–L4 including numeric comparison), property-based testing, adapter lifecycle, IsolatedRunner, MultiTierRunner, execution context with `$ref` resolution, verdict evaluation, snapshot record/replay, blob store, domain exception hierarchy, EchoOracle test utility. 413 tests, 100% coverage.
- **Phase 1b: elegua[wolfram]**: Port the Wolfram oracle HTTP server from sxAct into an optional extra. Generic kernel wrapper with configurable init/cleanup. **IN PROGRESS**.
- **Phase 2: Chacana-Spec**: Implementation of the standalone DSL and static type system.
- **Phase 3: xAct-jl**: Completion of the literal functional port.
- **Phase 4: Chacana-jl**: Development of the idiomatic Julia engine.

### 5. Non-Goals
- Support for non-symbolic numerical simulation.
- Direct integration with non-Python orchestrators.
- Domain-specific logic in the core (injected via adapters, expression builders, and init scripts).

### 6. Scientific Impact
Eleguá and Chacana represent a shift from porting code to verifying mathematics, providing an infrastructure of trust and a machine-parseable notation for physicists.
