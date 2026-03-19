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
- **Oracle Server Protocol**: Eleguá defines a standard HTTP contract for oracle servers (`/health`, `/evaluate-with-init`, `/cleanup`, `/check-state`). Any CAS that implements this contract can serve as an oracle.
- **Extension Model**: Domain-specific oracle servers are shipped as optional extras (e.g., `pip install elegua[wolfram]`). The core framework is transport-agnostic; extensions provide the bridge to specific compute engines.

## Tech Stack
- **Python 3.11+**: Core orchestration logic.
- **Pydantic**: Strict schema enforcement for tasks and tokens.
- **HTTP**: Primary transport between orchestrator and oracle servers. The `OracleClient` in core speaks the oracle protocol; server implementations live in optional extras.
- **Dolt/Beads**: Issue tracking and version-controlled metadata.

## Extension Model
Eleguá ships optional extras for specific compute engines. Each extra provides an oracle HTTP server, an adapter, and a Docker image:

| Extra | Install | Provides |
|-------|---------|----------|
| `elegua[wolfram]` | `pip install elegua[wolfram]` | Wolfram kernel oracle server, `WolframOracleAdapter`, Docker image |
| (future) | `pip install elegua[julia]` | Julia kernel oracle server |

Extensions accept **configurable init scripts and cleanup expressions** so that downstream projects (e.g., sxAct) can inject domain-specific setup (e.g., loading xAct) without modifying the extension itself.

## Project Conventions
- **Domain-Agnostic Core**: The core runner (Eleguá) MUST remain separate from domain-specific logic (Chacana). Domain-specific concerns are injected via adapters, expression builders, and init scripts.
- **Isolation First**: Kernels must be isolated to prevent "ghost state" leakage. Context isolation is enforced per-test via unique context IDs.
- **Verification-Driven**: All architectural changes must be verifiable through the multi-tier pipeline.
- **Extension over modification**: New compute engines are supported by adding optional extras, not by modifying the core.
