# Specification: Eleguá and Chacana Foundations RFC

## Purpose
This RFC defines the architectural pivot to decouple the `sxAct` project into two primary pillars: **Eleguá** (The Orchestrator) and **Chacana** (The Language). It establishes the three-tier execution strategy and the use of a common intermediate representation (CIR) for universal symbolic interchange.

## Requirements

### Requirement: Decoupling of DSL and Harness
The system SHALL separate the tensor calculus DSL (Chacana) from the test orchestration harness (Eleguá).

#### Scenario: Reuse Eleguá for different domains
- **WHEN** a new symbolic domain like RUBI is implemented
- **THEN** it MUST be possible to reuse the Eleguá orchestrator with a different domain plugin.

### Requirement: Three-Tier Verification
The system SHALL support verification across three distinct execution tiers to prove mathematical equivalence.

#### Scenario: Verify Tier 3 against Tier 1
- **WHEN** a result from the Chacana-jl engine (Tier 3) is compared
- **THEN** it MUST be verified against the Wolfram xAct "Gold Standard" (Tier 1).

## Design Details

### 1. The Three-Tier Strategy
- **Tier 1 (Wolfram xAct)**: The Gold Standard.
- **Tier 2 (xAct-jl)**: Literal Julia port.
- **Tier 3 (Chacana-jl)**: Idiomatic, high-performance Julia using `Symbolics.jl`.

### 2. Implementation Roadmap
- **Phase 1: Eleguá Core**: Generalization of the runner into a domain-agnostic orchestrator.
- **Phase 2: Chacana-Spec**: Implementation of the standalone DSL and static type system.
- **Phase 3: xAct-jl**: Completion of the literal functional port.
- **Phase 4: Chacana-jl**: Development of the idiomatic Julia engine.

### 3. Scientific Impact
Eleguá and Chacana represent a shift from porting code to verifying mathematics, providing an infrastructure of trust and a machine-parseable notation for physicists.
