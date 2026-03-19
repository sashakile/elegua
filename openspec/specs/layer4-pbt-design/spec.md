# Specification: Layer 2 Property Test Format and Runner Integration

## Metadata
- **Change-ID**: `REQ-PBT-001`
- **Version**: `1.4.0`
- **Status**: `IMPLEMENTED`
- **Last Updated**: 2026-03-19

## Purpose
This specification defines the format and runner integration for Layer 2 property-based testing in Eleguá. It enables language-agnostic mathematical property validation across different implementations by specifying invariants as declarative "for all X, P(X)" properties.

## Requirements

### Requirement: Declarative Property Format
The system SHALL parse a declarative TOML-based format for specifying mathematical properties, including generators and expected laws.

#### Scenario: Specify an involution property
- **GIVEN** a property TOML file with an `involution` property
- **WHEN** the runner loads the property
- **THEN** it MUST include a generator for input objects and a law stating that `f(f($x)) == $x`.

#### Scenario: Negative - Invalid TOML Schema
- **GIVEN** a property TOML file missing the required `law` field
- **WHEN** the runner attempts to parse the file
- **THEN** it MUST raise a `PropertyValidationError`.

### Requirement: Reproducible Property Runs
The property runner SHALL support reproducible test runs using a 64-bit integer random seed and the PCG64 random number generator.

#### Scenario: Reproduce a failing property test
- **GIVEN** a property test run that failed with seed `12345`
- **WHEN** the property test is re-run with `random_seed = 12345`
- **THEN** it MUST generate the exact same sequence of test inputs and results across all platforms.

#### Scenario: Edge Case - Zero Samples
- **GIVEN** a request to run 0 samples
- **WHEN** the command is executed
- **THEN** the runner MUST exit successfully with a warning: `No samples requested`.

## Design Details

### 1. Property Spec Format (JSON Schema)
Properties are stored in `tests/properties/` with a `layer = "property"` field.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "name": { "type": "string" },
    "layer": { "const": "property" },
    "generators": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": { "type": "string" },
          "type": { "type": "string", "description": "Domain-specific generator name" }
        },
        "required": ["name", "type"]
      }
    },
    "law": { "type": "string" },
    "setup": { "type": "array", "items": { "type": "string" } }
  },
  "required": ["name", "layer", "law"]
}
```

### 2. Runner Integration (Python API)
The primary interface is the `PropertyRunner` class:

```python
from elegua.property import PropertySpec, PropertyRunner, GeneratorRegistry

spec = PropertySpec.from_toml(Path("tests/properties/involution.toml"))
registry = GeneratorRegistry()
registry.register("integer", lambda rng: int(rng.integers(-1000, 1000)))

runner = PropertyRunner(registry=registry)
result = runner.run(spec, evaluator=my_evaluator, seed=42, samples=100)
```

**Parameters:**
- `samples`: Number of random inputs (default: 100).
- `seed`: 64-bit integer for PCG64 reproducibility.
- `evaluator`: Callable that checks if the property holds for given bindings.

**CLI:** Not yet implemented. Planned as `elegua-test run --layer 2`.

### 3. Backend: Custom Sampling
Uses a custom sampling backend (`sampling.py`) using the **PCG64** algorithm for cross-platform reproducibility.
- Supports variable substitution and domain-specific object generation via plugins.

### 4. Property Validation Modes
- **Single-adapter self-validation**: Validates that an adapter satisfies a mathematical law internally.
- **Cross-adapter comparison**: Ensures that two adapters agree on the same random inputs (using the same seed).

### 5. Failure Reporting and Counterexamples
When a property fails, the runner outputs:
- The failing sample number and seed offset.
- The substituted input values.
- The evaluated LHS and RHS.
- The discrepancy (delta or representation strings).

### 6. Implementation Status
Implemented in `src/elegua/property.py`:
- `PropertySpec` with `from_toml()` loader and `PropertyValidationError` for invalid schemas.
- `GeneratorRegistry` for domain-specific generator registration.
- `PropertyRunner` with `run()` and `generate_samples()`, PCG64-backed.
- `Failure` dataclass with `sample_index` and `bindings`.
- CLI (`xact-test property`) is NOT implemented. All functionality is Python API only.

### 7. Non-Goals
- Exhaustive symbolic proof (PBT is for sampling only).
- Direct performance benchmarking during PBT runs.
