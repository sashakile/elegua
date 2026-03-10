# Specification: Verification Baseline (Worked Examples)

## Purpose
This specification codifies the primary "Worked Examples" extracted from the original xAct documentation and research. It provides a concrete mathematical baseline that all Eleguá tiers must satisfy to prove 1:1 parity.

## Requirements

### Requirement: Symmetric/Antisymmetric Swap Parity
The system SHALL correctly simplify swapped indices for tensors with permutation symmetry.

#### Scenario: Symmetric tensor swap
- **WHEN** an expression `Cns[-cna, -cnb] - Cns[-cnb, -cna]` is evaluated
- **THEN** it MUST result in `"0"` if `Cns` is declared symmetric.

#### Scenario: Antisymmetric tensor swap
- **WHEN** an expression `Cna[-cna, -cnb] + Cna[-cnb, -cna]` is evaluated
- **THEN** it MUST result in `"0"` if `Cna` is declared antisymmetric.

### Requirement: Riemann Monoterm Symmetries
The system SHALL correctly handle the 8-element monoterm symmetry group of the Riemann tensor.

#### Scenario: Riemann first-pair antisymmetry
- **WHEN** `RiemannCnd[-cna, -cnb, -cnc, -cnd] + RiemannCnd[-cnb, -cna, -cnc, -cnd]` is evaluated
- **THEN** it MUST result in `"0"`.

### Requirement: Product Idempotency
The system SHALL maintain canonical ordering in tensor products to ensure idempotency.

#### Scenario: Kretschmann invariant canonicalization
- **WHEN** a product like `R[-a,-b,-c,-d] R[a,b,c,d]` is canonicalized
- **THEN** it MUST produce the same string regardless of the input term order.

## Design Details

### 1. Baseline Examples from sxAct
These examples are based on the Tier 1 (Wolfram xAct) "Gold Standard" output:
- **Example 1**: `Cns[-cna, -cnb] - Cns[-cnb, -cna]` -> `"0"`
- **Example 2**: `Cna[-cna, -cnb] + Cna[-cnb, -cna]` -> `"0"`
- **Example 3**: `RiemannCnd[-cna, -cnb, -cnc, -cnd] + RiemannCnd[-cnb, -cna, -cnc, -cnd]` -> `"0"`
- **Example 4**: `Cns[-cna, -cnb] + Cnv[cna]` -> No simplification, order preserved.
- **Example 5**: `RiemannCID[-cia,-cib,-cic,-cid] RiemannCID[cia,cib,cic,cid] - RiemannCID[-cic,-cid,-cia,-cib] RiemannCID[cic,cid,cia,cib]` -> `"0"`
