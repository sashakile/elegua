# Specification: Three-Layer Testing Architecture

## Purpose
This specification defines the three-layer testing architecture for the xAct migration project. It ensures that the migration from Wolfram Mathematica to Julia and Python is mathematically correct, performant, and serves as a foundation for language-agnostic mathematical property specifications.

## Requirements

### Requirement: Migration Validation
The testing architecture SHALL validate the functional equivalence and performance of the migrated implementation (Julia/Python) against the Wolfram xAct oracle.

#### Scenario: Validate tensor contraction
- **WHEN** a tensor contraction is executed in Julia
- **THEN** the result MUST match the Wolfram xAct oracle within numerical tolerance.

### Requirement: Language-Agnostic Property Specification
The architecture SHALL support property-based tests that describe mathematical laws independent of the specific implementation language.

#### Scenario: Verify associativity of tensor contraction
- **WHEN** a property-based test for associativity is run
- **THEN** it MUST hold across Wolfram, Julia, and Python implementations.

## Design Details

### 1. Architecture Overview
The framework uses **three testing layers** that serve both migration and research goals:
- **Layer 1**: Unit tests (concrete examples, oracle validation)
- **Layer 2**: Property-based tests (mathematical invariants, reusable specifications)
- **Layer 3**: Performance regression tests (usability tracking)

### 2. Layer 1: Unit Tests (Gold Standard Cases)
Concrete examples with known inputs/outputs for debugging and validation.
- Fixed inputs with exact expected outputs.
- Oracle (Wolfram xAct) provides ground truth.
- Extracted from documentation notebooks.

### 3. Layer 2: Property-Based Tests (Mathematical Laws)
Encode mathematical invariants as executable, language-agnostic specifications.
- Randomly generated test inputs.
- Describes mathematical laws (associativity, commutativity, distributivity, etc.).
- Implementation-independent.
- Explores edge cases automatically.

### 4. Layer 3: Performance Regression Tests
Ensure implementations are usable through performance tracking and regression prevention.
- Tracks execution time, memory, compilation overhead.
- Compares against Wolfram baseline (usability threshold).
- Compares against previous versions (regression detection).

### 5. Why Mutation Testing Is Not Needed
Mutation testing is not required as the framework already provides stronger validation through oracle comparison (Layer 1) and mathematical law violations (Layer 2).
