## MODIFIED Requirements

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

## ADDED Requirements

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
