# Specification: Tensor Domain Implementation (XPerm.jl / XTensor.jl)

## Metadata
- **Change-ID**: `REQ-TENSOR-CORE-001`
- **Version**: `1.2.0`
- **Status**: `PROPOSAL`
- **Domain**: `Tensor Calculus`
- **Last Updated**: 2026-03-17

## Purpose
This specification defines the design and implementation of the `XPerm.jl` and `XTensor.jl` Julia modules, which provide the core tensor algebra and permutation group canonicalization engines. These modules ensure that the Julia implementation achieves mathematical parity with the original Wolfram xAct suite by passing the `verification-baseline` suite.

## Requirements

### Requirement: Canonicalization Parity
The system SHALL achieve 100% mathematical parity for tensor index canonicalization using the Butler-Portugal algorithm.

#### Scenario: Canonicalize a symmetric tensor swap
- **GIVEN** a symmetric tensor `Cns`
- **WHEN** the expression `Cns[-cna, -cnb] - Cns[-cnb, -cna]` is canonicalized
- **THEN** it MUST simplify to `"0"`.

#### Scenario: Negative - Redefinition Error
- **GIVEN** an existing tensor `T`
- **WHEN** `DefTensor` is called with the same name `T`
- **THEN** the system MUST raise a `RedefinitionError`.

### Requirement: Automatic Curvature Tensor Creation
The system SHALL automatically create related curvature tensors (Riemann, Ricci, Einstein) when a metric is defined via `DefMetric`.

#### Scenario: Auto-create Riemann tensor
- **GIVEN** a manifold `M`
- **WHEN** `DefMetric[-1, g[-a,-b], CD]` is called
- **THEN** the `RiemannCD`, `RicciCD`, and `EinsteinCD` tensors MUST be automatically registered in the global state.

## Design Details

### 1. Data Structures (Julia)
```julia
struct TensorObj
    name::Symbol
    indices::Vector{Symbol}
    symmetry::SymmetrySpec
    manifold::Symbol
end

struct SymmetrySpec
    type::Symbol # :Symmetric, :Antisymmetric, :Riemann
    permutation_group::PermGroup # Strong Generating Set
end
```

### 2. API Signatures (XTensor.jl)
- `DefManifold(name::Symbol, dim::Int, indices::Vector{Symbol})`
- `DefTensor(name::Symbol, indices::Vector{Symbol}, symmetry::Symbol)`
- `DefMetric(signature::Int, tensor::Expression, connection::Symbol)`
- `ToCanonical(expr::Expression)::Expression`

### 3. XPerm.jl Algorithms
- **Schreier-Sims**: Builds a strong generating set for a permutation group.
- **Butler-Portugal**: Finds the lex-minimum element of a double coset for dummy index exchange.

### 4. Non-Goals
- Support for non-Riemannian geometries (e.g., torsion-full connections).
- GPU acceleration (CPU-only for initial parity).

### 5. Negative Scenarios
- **Invalid Bundle**: Calling `DefTensor` on a manifold that has not been defined MUST raise a `ManifoldNotFoundError`.
- **Index Mismatch**: Defining a tensor with 4 indices but providing a symmetry spec for 2 indices MUST raise an `IndexSymmetryMismatchError`.
