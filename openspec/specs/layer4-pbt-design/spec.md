# Specification: Layer 2 Property Test Format and Runner Integration

## Purpose
This specification defines the format and runner integration for Layer 2 property-based testing in Eleguá. It enables language-agnostic mathematical property validation across different implementations (Wolfram, Julia, Python) by specifying invariants as declarative "for all X, P(X)" properties.

## Requirements

### Requirement: Declarative Property Format
The system SHALL support a declarative TOML-based format for specifying mathematical properties, including generators and expected laws.

#### Scenario: Specify an involution property
- **WHEN** a property TOML is loaded with a `dagger_involution` property
- **THEN** it MUST include a generator for symbols and a law stating that `MakeDaggerSymbol[MakeDaggerSymbol[$s]] == $s`.

### Requirement: Reproducible Property Runs
The property runner SHALL support reproducible test runs using configurable random seeds.

#### Scenario: Reproduce a failing property test
- **WHEN** a property test is run with a specific `random_seed`
- **THEN** it MUST generate the exact same sequence of test inputs and results.

## Design Details

### 1. Property Spec Format
Uses a separate TOML format in `tests/properties/` with `layer = "property"`.
- Supports variable substitution syntax (`$name`).
- Includes `[[setup]]` blocks for manifold/metric context.
- Supports different equivalence types (`identical`, `numerical_tolerance`).

### 2. Runner Integration
A new `xact-test property` CLI subcommand is introduced to execute property tests.
- Supports filtering by tag.
- Allows overriding sample count and seed.

### 3. Backend: Custom Sampling
Uses a custom sampling backend (`sampling.py`) to maintain language-agnostic property validation across Wolfram, Julia, and Python.
- Supports scalar variable substitution and tensor component array generation.

### 4. Property Validation Modes
- **Single-adapter self-validation**: Validates that an adapter satisfies a mathematical law internally.
- **Cross-adapter comparison**: Ensures that two adapters agree on the same random inputs (using the same seed).

### 5. Failure Reporting and Counterexamples
When a property fails, the runner outputs:
- The failing sample number and seed offset.
- The substituted input values.
- The evaluated LHS and RHS.
- The discrepancy (delta or representation strings).
