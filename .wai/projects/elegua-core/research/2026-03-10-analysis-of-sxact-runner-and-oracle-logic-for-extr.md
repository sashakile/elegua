# Research: Analysis of sxAct runner and oracle logic for extraction

**Date:** 2026-03-10
**Project:** elegua-core
**Status:** Completed

## Background
The current `sxact` test runner and oracle client are tightly coupled to the tensor calculus domain. The logic for managing kernels, executing actions, and comparing results assumes that the payload is always a tensor expression and the oracle is always Wolfram/xAct.

## Methodology
Analyzed the following components in the `sxAct` repository:
1. `packages/sxact/src/sxact/runner/`: Identifies tight coupling between task execution and tensor-specific serialization.
2. `packages/sxact/src/sxact/oracle/`: Analyzes the `OracleClient` and its reliance on Mathematica-specific communication protocols.
3. `packages/sxact/src/sxact/compare/`: Reviews the comparison logic which currently relies on string-to-string translation (`_wl_to_jl`).

## Findings

### 1. Tight Coupling Symptoms
- **Payload Specificity**: The runner expects `DefTensor` or `ToCanonical` actions, making it difficult to test other symbolic systems (e.g., RUBI).
- **Comparison Logic**: The 4-Layer Comparison Pipeline is conceptually sound but lacks a formal `ValidationToken` (JSON AST) structure, forcing reliance on fragile string comparisons.
- **Oracle Dependency**: The kernel management logic is specialized for WolframEngine, lacking a generic `Adapter` interface for other high-fidelity oracles.

### 2. Extraction Strategy
To transform this into a domain-agnostic orchestrator (**Eleguá**), we must:
1. **Genericize the Task Model**: Move to an `EleguaTask` that accepts arbitrary JSON payloads.
2. **Formalize the Protocol**: Define a `ValidationToken` using a MathJSON-compatible structure to eliminate string-translation dependency.
3. **Implement Adapter Interface**: Decouple the orchestrator from the specific kernel by defining a standard `Adapter` contract for `initialize`, `execute`, and `teardown`.

## Next Steps
- Implement the `EleguaTask` state machine.
- Define the JSON schema for `ValidationToken`.
- Extract the common `Adapter` base class.
