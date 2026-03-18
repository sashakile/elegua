# Project Context: Eleguá and Chacana

## Vision
The project provides an **infrastructure of trust** for the migration of complex mathematical systems. It is divided into two primary pillars:

- **Eleguá (The Orchestrator)**: A domain-agnostic, multi-tier test harness. It manages the lifecycle of validation tasks and proves functional equivalence between a high-fidelity Oracle and multiple implementations.
- **Chacana (The Language)**: A tensor calculus domain implemented using Eleguá's generic framework.

## Key Concepts
- **Three-Tier Execution**:
    - **Tier 1**: High-Fidelity Oracle (e.g., Wolfram xAct).
    - **Tier 2**: Literal Port (e.g., xAct-jl).
    - **Tier 3**: Idiomatic Target (e.g., Chacana-jl).
- **EleguaTask**: The atomic unit of validation, including manifest loading, multi-tier execution, and 4-layer comparison.
- **4-Layer Comparison Pipeline**:
    1. **Identity**: Bitwise/Hash.
    2. **Structural**: AST isomorphism.
    3. **Canonical**: Normalizer-based semantic equivalence (Domain-Specific).
    4. **Invariant**: Numerical sampling and Property-Based Testing (Domain-Specific).

## Tech Stack
- **Python 3.10+**: Core orchestration logic.
- **Pydantic**: Strict schema enforcement for tasks and tokens.
- **MathJSON-compatible AST**: Universal symbolic interchange format.
- **IPC**: Subprocesses and ZMQ/TCP for persistent kernel communication.
- **Dolt/Beads**: Issue tracking and version-controlled metadata.

## Project Conventions
- **Domain-Agnostic Core**: The core runner (Eleguá) MUST remain separate from domain-specific logic (Chacana).
- **Isolation First**: Kernels must be isolated to prevent "ghost state" leakage.
- **Verification-Driven**: All architectural changes must be verifiable through the multi-tier pipeline.
