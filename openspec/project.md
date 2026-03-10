# Project Context: Eleguá

## Purpose
**Eleguá** (Master of the Crossroads) is a domain-agnostic, multi-tier test harness designed to validate the mathematical equivalence of symbolic computing systems during migration (e.g., from Wolfram Mathematica to Julia/Python). It provides an **infrastructure of trust** by orchestrating communication between an **Oracle** (Ground Truth) and one or more **Implementations Under Test (IUT)**.

## Core Concepts
- **The Orchestrator**: Manages the lifecycle of validation tasks.
- **Three-Tier Execution**:
    - **Tier 1**: Wolfram xAct (The "Gold Standard" Oracle).
    - **Tier 2**: xAct-jl (Literal Julia Port / "High-Speed Oracle").
    - **Tier 3**: Chacana-jl (Idiomatic Julia / The Performance Future).
- **EleguaTask**: The atomic unit of validation, including manifest loading, multi-tier execution, and comparison.
- **4-Layer Comparison Pipeline**:
    1. **Identity**: Bitwise/Hash.
    2. **Structural**: AST isomorphism.
    3. **Canonical**: Normalizer-based semantic equivalence.
    4. **Invariant**: Numerical sampling and Property-Based Testing (PBT).

## Tech Stack
- **Python 3.10+**: Core orchestration logic.
- **Pydantic**: Strict schema enforcement for tasks and tokens.
- **MathJSON-compatible AST**: Universal symbolic interchange format.
- **IPC**: Subprocesses and ZMQ/TCP for persistent kernel communication.
- **Dolt/Beads**: Issue tracking and version-controlled metadata.

## Project Conventions
- **Isolation First**: Kernels must be isolated to prevent "ghost state" leakage (Mathematica Contexts, Julia Subprocesses).
- **Verification-Driven**: All architectural changes must be verifiable through the multi-tier pipeline.
- **Domain-Agnostic Core**: Keep the core runner separate from domain-specific plugins (like Chacana).

## Domain Context
- **Symbolic Migration**: The high-stakes process of porting mathematical libraries where "almost correct" is failure.
- **Tensor Calculus**: The primary initial domain, though the system is designed for general symbolic algebra (e.g., RUBI, FeynCalc).
