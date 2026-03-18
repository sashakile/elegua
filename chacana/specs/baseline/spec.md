# Specification: Tensor Domain Verification Baseline

## Metadata
- **Change-ID**: `REQ-TENSOR-BASE-001`
- **Version**: `1.2.0`
- **Status**: `PROPOSAL`
- **Domain**: `Tensor Calculus`
- **Last Updated**: 2026-03-17

## Purpose
This specification codifies the primary "Worked Examples" extracted from the original xAct documentation and research. It provides a concrete mathematical baseline that all Eleguá tiers must satisfy to prove 1:1 parity using the MathJSON (v1.0) format.

## Requirements

### Requirement: Symmetric/Antisymmetric Swap Parity
The system SHALL simplify swapped indices for tensors with permutation symmetry.

#### Scenario: Symmetric tensor swap
- **GIVEN** a symmetric tensor `Cns` defined in `manifest.toml`
- **WHEN** the expression `Cns[-cna, -cnb] - Cns[-cnb, -cna]` is evaluated
- **THEN** it MUST simplify to the string `"0"`.

#### Scenario: Negative - Undeclared Tensor
- **GIVEN** an expression with an undeclared tensor `X`
- **WHEN** evaluation is attempted
- **THEN** the adapter MUST return an `UNDECLARED_SYMBOL` error.

### Requirement: Riemann Monoterm Symmetries
The system SHALL handle the 8-element monoterm symmetry group of the Riemann tensor:
- First pair antisymmetry: `R[a,b,c,d] == -R[b,a,c,d]`
- Second pair antisymmetry: `R[a,b,c,d] == -R[a,b,d,c]`
- Pair exchange symmetry: `R[a,b,c,d] == R[c,d,a,b]`

#### Scenario: Riemann first-pair antisymmetry
- **GIVEN** a Riemann tensor declared in the manifest
- **WHEN** `R[-a, -b, -c, -d] + R[-b, -a, -c, -d]` is evaluated
- **THEN** it MUST simplify to `"0"`.

### Requirement: Product Idempotency
The system SHALL maintain canonical ordering in tensor products to ensure idempotency.

#### Scenario: Kretschmann invariant canonicalization
- **GIVEN** two different input orderings of the Kretschmann product
- **WHEN** `ToCanonical` is applied to both
- **THEN** both MUST produce the exact same MathJSON string representation.

## Design Details

### 1. Baseline Data Format (JSON Schema)
```json
{
  "change_id": "BASE-001",
  "cases": [
    {
      "name": "RiemannSwap",
      "manifest": "manifest.toml",
      "expression": { "fn": "Add", "args": [...] },
      "expected": "0"
    }
  ]
}
```

### 2. Manifest Definition (manifest.toml)
```toml
[tensors]
Cns = { symmetry = "Symmetric", indices = ["-a", "-b"] }
Cna = { symmetry = "Antisymmetric", indices = ["-a", "-b"] }
Riemann = { symmetry = "Riemann", indices = ["-a", "-b", "-c", "-d"] }
```

### 3. Worked Examples from sxAct
These examples are based on the Tier 1 (Wolfram xAct) "Gold Standard" output:
- **Example 1**: `Cns[-cna, -cnb] - Cns[-cnb, -cna]` -> `"0"`
- **Example 2**: `Cna[-cna, -cnb] + Cna[-cnb, -cna]` -> `"0"`
- **Example 3**: `Riemann[-a, -b, -c, -d] + Riemann[-b, -a, -c, -d]` -> `"0"`
- **Example 4**: `Cns[-cna, -cnb] + Cnv[cna]` -> No simplification, order preserved.
- **Example 5**: `R[-a,-b,-c,-d] R[a,b,c,d] - R[-c,-d,-a,-b] R[c,d,a,b]` -> `"0"`

### 4. Non-Goals
- Support for non-tensor symmetries (e.g., Lie Algebra structure constants).
- Direct performance measurement during baseline runs.
