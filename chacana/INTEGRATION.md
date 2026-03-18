# Tensor Calculus Domain Integration Guide

This guide documents how the generic **Eleguá** orchestrator is applied to the **Tensor Calculus** domain (specifically for the xAct migration to Julia/Python).

## 1. Role Mapping
| Eleguá Role | Tensor Domain Implementation |
| :--- | :--- |
| **High-Fidelity Oracle** | Wolfram Mathematica with `xAct` package. |
| **IUT (Tier 2)** | `xAct-jl` (Literal Julia port). |
| **IUT (Tier 3)** | `Chacana-jl` (Idiomatic Julia with `Symbolics.jl`). |

## 2. Action Definitions
The tensor domain implements the following actions within the `ActionPayload`:
- `DefManifold`: Defines the underlying topological space.
- `DefTensor`: Declares a tensor with specific index symmetries.
- `DefMetric`: Defines a metric and associated curvature tensors.
- `ToCanonical`: Simplifies an expression to its unique canonical representative.

## 3. Data Formats

### 3.1 ValidationToken (MathJSON)
The tensor domain uses MathJSON to represent tensor expressions.
- **Tensors**: Represented as function calls where the head is the tensor name and arguments are the indices (e.g., `["T", "-a", "-b"]`).
- **Contractions**: Implicitly handled via repeated indices.

### 3.2 Property-Based Testing (Layer 2)
Tensor-specific generators implemented in `sampling.py`:
- `Symbol`: Randomly generated dummy indices.
- `Tensor`: Randomly generated tensor objects with specific symmetries.
- `Scalar`: Numerical values for sampling poles.

## 4. Specific Symmetries
Eleguá's **Layer 3 (Canonical)** comparison utilizes the `XPerm.jl` plugin to handle:
- Permutation symmetries (Symmetric, Antisymmetric).
- Monoterm symmetries (Riemann).
- Multi-term symmetries (Bianchi).

## 5. Domain Specifications
Detailed specifications for the tensor domain are found in:
- `chacana/specs/baseline/spec.md`: Concrete worked examples.
- `chacana/specs/core/spec.md`: Internal Julia implementation details.

## 6. Implementation Notes
- **Isolation**: Wolfram kernels are isolated using `Context` scoping. Julia kernels are isolated via subprocesses.
- **Normalization**: The `ToCanonical` action acts as the primary normalizer for Layer 3 comparison.
