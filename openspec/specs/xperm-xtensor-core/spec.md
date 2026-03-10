# Specification: XPerm.jl and XTensor.jl Design

## Purpose
This specification defines the design and implementation of the `XPerm.jl` and `XTensor.jl` Julia modules, which provide the core tensor algebra and permutation group canonicalization engines for the xAct migration project. These modules ensure that the Julia implementation achieves mathematical parity with the original Wolfram xAct suite.

## Requirements

### Requirement: Canonicalization Parity
The system SHALL achieve 100% mathematical parity for tensor index canonicalization using the Butler-Portugal algorithm.

#### Scenario: Canonicalize a symmetric tensor swap
- **WHEN** an expression like `Cns[-cna, -cnb] - Cns[-cnb, -cna]` is canonicalized (where `Cns` is symmetric)
- **THEN** it MUST simplify to `"0"`.

### Requirement: Automatic Curvature Tensor Creation
The system SHALL automatically create related curvature tensors when a metric is defined.

#### Scenario: Auto-create Riemann tensor
- **WHEN** a metric is defined using `DefMetric`
- **THEN** the `Riemann`, `Ricci`, and `Einstein` tensors MUST be automatically registered.

## Design Details

### 1. XPerm.jl Design
- **Permutation Representation**: 1-indexed image vectors, including signed permutations for antisymmetric groups.
- **Algorithms**:
    - **Schreier-Sims**: Builds a strong generating set for a permutation group.
    - **Right Coset Representative**: Finds the lex-minimum element of a right coset.
    - **Double Coset Representative**: Handles dummy index exchange group canonicalization (Tier 2).
    - **Shortcuts**: Optimized sorting for symmetric and antisymmetric groups.

### 2. XTensor.jl Design
- **Data Structures**: `ManifoldObj`, `VBundleObj`, `TensorObj`, `MetricObj`, `IndexSpec`, and `SymmetrySpec`.
- **Global State**: Managed using dictionaries and ordered lists (e.g., `_manifolds`, `Manifolds`).
- **Action Implementations**: `DefManifold`, `DefTensor`, `DefMetric`, `ToCanonical`.

### 3. Tensor Expression Parser and ToCanonical Pipeline
- **Grammar**: Handles sums and products of tensor monomials with integer coefficients.
- **Canonicalization Pipeline**: Applies symmetry shortcuts or Butler-Portugal to each tensor factor, then collects like terms.

### 4. Adapter Integration
- **JuliaAdapter**: lazily loads `XPerm.jl` and `XTensor.jl`, dispatches actions, and manages symbol binding in `Main` scope.
- **PythonAdapter**: Shares the same Julia XTensor state and dispatch logic as `JuliaAdapter`.
