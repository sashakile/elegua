# Specification: Layer 2 Property Test Format and Runner Integration

## Metadata
- **Change-ID**: `REQ-PBT-001`
- **Version**: `2.0.0`
- **Status**: `IMPLEMENTED`
- **Last Updated**: 2026-03-24

## Purpose
This specification defines the format and runner integration for Layer 2 property-based testing in Eleguá. It enables language-agnostic mathematical property validation across different implementations by specifying invariants as declarative "for all X, P(X)" properties, backed by [Hypothesis](https://hypothesis.readthedocs.io/) for shrinking, composable strategies, and example databases.

## Requirements

### Requirement: Declarative Property Format
The system SHALL parse a declarative TOML-based format for specifying mathematical properties, including Hypothesis strategies (via type names) and expected laws. Generator entries MAY include an optional `params` table and the spec MAY include a `[settings]` table.

#### Scenario: Specify an involution property
- **GIVEN** a property TOML file with an `involution` property
- **WHEN** the runner loads the property
- **THEN** it MUST include a strategy for input objects and a law stating that `f(f($x)) == $x`.

#### Scenario: Negative - Invalid TOML Schema
- **GIVEN** a property TOML file missing the required `law` field
- **WHEN** the runner attempts to parse the file
- **THEN** it MUST raise a `PropertyValidationError`.

#### Scenario: Generator with strategy parameters
- **GIVEN** a property TOML with `[generators.params]` containing `min_value` and `max_value`
- **WHEN** the runner loads the property
- **THEN** it MUST pass the params as kwargs to the strategy factory registered for that type.

#### Scenario: Settings override
- **GIVEN** a property TOML with `[settings]` containing `max_examples = 200`
- **WHEN** the runner executes the property
- **THEN** Hypothesis MUST run at most 200 examples.

### Requirement: Reproducible Property Runs
The property runner SHALL support reproducible test runs via the Hypothesis example database. Failing inputs are persisted and replayed on subsequent runs. Cross-platform deterministic seeding (PCG64) is reserved for L4 numeric comparison only.

#### Scenario: Reproduce a failing property via example database
- **GIVEN** a property test that previously failed
- **WHEN** the property test is re-run
- **THEN** Hypothesis MUST replay the stored failing example before exploring new inputs.

#### Scenario: Edge Case - Zero max_examples
- **GIVEN** a request to run with `max_examples = 0`
- **WHEN** the command is executed
- **THEN** the runner MUST exit successfully with no examples tested.

### Requirement: Counterexample Shrinking
The property runner SHALL automatically shrink failing inputs to a minimal counterexample using Hypothesis's shrinking infrastructure.

#### Scenario: Shrink a failing integer input
- **GIVEN** a property law that fails for negative integers
- **WHEN** the runner finds a failing input (e.g., `-847`)
- **THEN** it MUST shrink the input to a minimal counterexample (e.g., `-1`).

#### Scenario: Shrunk counterexample in failure report
- **GIVEN** a property that fails
- **WHEN** the `PropertyResult` is returned
- **THEN** each `Failure` MUST include `shrunk_bindings` containing the minimal counterexample.

### Requirement: Composable Strategy Registration
The property runner SHALL support composable Hypothesis strategies via a `StrategyRegistry`, replacing the flat callable-based `GeneratorRegistry`.

#### Scenario: Register a Hypothesis strategy
- **GIVEN** a `StrategyRegistry` instance
- **WHEN** `registry.register("integer", st.integers(-1000, 1000))` is called
- **THEN** the strategy MUST be available for property specs with `type = "integer"`.

#### Scenario: Compose strategies
- **GIVEN** a `StrategyRegistry` with registered base strategies
- **WHEN** a strategy is built using `st.builds(make_tensor, dim=st.integers(2, 6))`
- **THEN** Hypothesis MUST be able to generate, shrink, and display values from the composed strategy.

#### Scenario: Backward compatibility with GeneratorRegistry
- **GIVEN** code using the deprecated `GeneratorRegistry` API
- **WHEN** a callable `lambda rng: rng.integers(-1000, 1000)` is registered
- **THEN** it MUST be wrapped in a Hypothesis strategy and a deprecation warning emitted.

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
          "type": { "type": "string", "description": "Hypothesis strategy name in registry" },
          "params": { "type": "object", "description": "Optional kwargs for strategy factory" }
        },
        "required": ["name", "type"]
      }
    },
    "law": { "type": "string" },
    "setup": { "type": "array", "items": { "type": "string" } },
    "settings": {
      "type": "object",
      "properties": {
        "max_examples": { "type": "integer", "default": 100 },
        "deadline": { "type": ["integer", "null"], "default": 1000 }
      }
    }
  },
  "required": ["name", "layer", "law"]
}
```

### 2. Runner Integration (Python API)
The primary interface is `PropertyRunner` with `StrategyRegistry`:

```python
from hypothesis import strategies as st
from elegua.property import PropertySpec, PropertyRunner, StrategyRegistry

spec = PropertySpec.from_toml(Path("tests/properties/involution.toml"))
registry = StrategyRegistry()
registry.register("integer", st.integers(-1000, 1000))

runner = PropertyRunner(registry=registry)
result = runner.run(spec, evaluator=my_evaluator)
```

**Parameters:**
- `evaluator`: Callable `(law, bindings) -> bool` that checks if the property holds.
- `max_examples`: Override max examples (default: from spec settings, 100).
- `deadline`: Override deadline in ms (default: from spec settings, 1000). Pass `None` to disable.

**CLI:** Not yet implemented. Planned as `elegua-test run --layer 2`.

### 3. Backend: Hypothesis
Uses [Hypothesis](https://hypothesis.readthedocs.io/) for:
- **Shrinking**: Failing inputs automatically reduced to minimal counterexamples.
- **Composable strategies**: `st.integers()`, `st.builds()`, `st.one_of()`, etc.
- **Example database**: Past failures persisted and replayed first.
- **Health checks**: Detection of degenerate generators, too-slow tests.

PCG64 cross-platform sampling is **not** used for PBT — it remains in `compare_numeric.py` for L4 cross-CAS numeric comparison only.

### 4. Strategy Registry

`StrategyRegistry` maps TOML type names to Hypothesis strategies:

| Entry type | Example | Params behavior |
|---|---|---|
| Pre-built `SearchStrategy` | `st.integers(-100, 100)` | Params ignored |
| Callable factory | `lambda min_value=0, max_value=100: st.integers(min_value, max_value)` | Params passed as kwargs |

`GeneratorRegistry` is kept as a deprecated alias that wraps callables in `st.builds()` and emits `DeprecationWarning`.

### 5. Property Validation Modes
- **Single-adapter self-validation**: Validates that an adapter satisfies a mathematical law internally.
- **Cross-adapter comparison**: Ensures that two adapters agree on the same random inputs.

### 6. Failure Reporting and Counterexamples
When a property fails, each `Failure` includes:
- `sample_index`: Which sample triggered the failure.
- `bindings`: The variable values at the point of failure.
- `shrunk_bindings`: The minimal counterexample after Hypothesis shrinking.

### 7. Implementation Status
Implemented in `src/elegua/property.py`:
- `PropertySpec` with `from_toml()` loader, `GeneratorSpec` with optional `params`, `PropertySettings`.
- `StrategyRegistry` for Hypothesis strategy registration (pre-built or factory).
- `GeneratorRegistry` as deprecated alias wrapping callables in `st.builds()`.
- `PropertyRunner` backed by `hypothesis.given`, with shrinking and health checks.
- `Failure` dataclass with `sample_index`, `bindings`, and `shrunk_bindings`.
- `PropertyResult` with `passed`, `samples_run`, `failures`.
- CLI is NOT implemented. Planned as `elegua-test run --layer 2`.

### 8. Non-Goals
- Exhaustive symbolic proof (PBT is for sampling only).
- Direct performance benchmarking during PBT runs.
- Stateful testing via TOML (available via Python API only).
- Replacing L4 numeric comparison (PCG64 stays for cross-CAS sampling).
