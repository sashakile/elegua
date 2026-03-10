# Design: Multi-tier validation architecture with SHA-256 Blob Store

**Date:** 2026-03-10
**Project:** elegua-core
**Status:** Decided

## Context
Validating the migration of complex mathematical systems (like xAct) requires a rigorous, multi-tier execution strategy to prove mathematical equivalence across different implementations and languages.

## Decision: The Three-Tier Execution Model
To verify correctness, we will orchestrate symbolic tasks across three levels of fidelity:

| Tier | Name | Description | Role |
| :--- | :--- | :--- | :--- |
| **Tier 1** | **Wolfram Oracle** | The original "Gold Standard" suite (xAct). | Ultimate Ground Truth. |
| **Tier 2** | **Mirror Oracle** | A literal, feature-complete port (e.g., xAct-jl). | High-speed Oracle. |
| **Tier 3** | **New Engine** | An idiomatic, performant engine (e.g., Chacana-jl). | Target implementation. |

## Decision: SHA-256 Blob Store for Large Payloads
Symbolic expressions in General Relativity can exceed 1MB in their serialized form, causing recursion issues in standard JSON parsers and excessive memory overhead.

1. **Reference-by-Hash**: Payloads >1MB are replaced with a `{"blob": "<hash>"}` reference in the `ValidationToken`.
2. **Algorithm**: Use SHA-256 for deterministic, collision-resistant hashing.
3. **Directory Structure**: Store blobs in a two-level nested directory structure (e.g., `.elegua/blobs/ab/cd...`) based on the hash to ensure file system performance with thousands of entries.
4. **Lifecycle**: Blobs are persisted to enable offline "Record & Replay," allowing Tier 2/3 validation in CI/CD environments without a live Wolfram license.

## Decision: Multi-Protocol IPC
To accommodate different implementation languages and runtime requirements, Eleguá supports multiple Inter-Process Communication (IPC) strategies:
- **Subprocess (Standard)**: Direct stdin/stdout for quick one-off kernels.
- **ZMQ/TCP (Persistent)**: High-speed, long-lived sockets for persistent symbolic kernels (e.g., Wolfram Engine, Julia).

## Rationale
The 3-Tier model provides a tiered infrastructure of trust, where each implementation can be validated against a higher-fidelity source. The Blob Store ensures the orchestrator remains performant even when handling the extremely large expressions typical of higher-order perturbation theory.

## Consequences
- **Positive**: Enables rigorous, automated verification of complex math.
- **Negative**: Adds complexity to the orchestrator to manage multiple concurrent kernels and a local blob cache.
- **Dependency**: Requires a consistent `ValidationToken` format across all adapters.
