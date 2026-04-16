## ADDED Requirements

### Requirement: Declarative Layer Key Exclusion
The comparison pipeline SHALL support per-layer key exclusion sets so that layers do not hardcode knowledge of other layers' data fields.

#### Scenario: Register layer with exclusion keys
- **GIVEN** a `ComparisonPipeline` instance
- **WHEN** `pipeline.register(4, "numeric", fn, exclude_keys=frozenset({"numeric_samples"}))` is called
- **THEN** layers with `num < 4` MUST exclude `numeric_samples` from the result dicts before comparison.

#### Scenario: No exclusion keys (backward compatibility)
- **GIVEN** a `ComparisonPipeline` instance
- **WHEN** `pipeline.register(3, "canonical", fn)` is called without `exclude_keys`
- **THEN** the layer MUST operate on unmodified result dicts (empty exclusion set by default).

#### Scenario: Multiple layers with exclusion keys
- **GIVEN** layers 3 and 4 both declare `exclude_keys`
- **WHEN** layer 1 runs
- **THEN** it MUST see results with keys from both layer 3 and layer 4 excluded.

### Requirement: Injectable Result Mapper
`OracleAdapter` SHALL accept an optional `result_mapper` callable that translates oracle response dicts into `ValidationToken`, enabling domain-specific result mapping without subclassing.

#### Scenario: Custom result mapper
- **GIVEN** an `OracleAdapter` constructed with a `result_mapper` callable
- **WHEN** `execute(task)` receives a response from the oracle
- **THEN** the `result_mapper` MUST be called with `(action, payload, data)` to produce the `ValidationToken`.

#### Scenario: Default result mapper
- **GIVEN** an `OracleAdapter` constructed without a `result_mapper`
- **WHEN** `execute(task)` receives a response from the oracle
- **THEN** the built-in `_map_result()` logic MUST be used (Assert handling, status mapping, metadata extraction).

### Requirement: Runner Deprecation
`load_toml_tasks()` and `run_tasks()` in `runner.py` SHALL emit `DeprecationWarning` directing callers to `load_test_file()` and `IsolatedRunner`.

#### Scenario: load_toml_tasks emits deprecation warning
- **GIVEN** a caller invoking `load_toml_tasks(path)`
- **WHEN** the function executes
- **THEN** a `DeprecationWarning` MUST be emitted with a message referencing `load_test_file()` as the replacement.

#### Scenario: run_tasks emits deprecation warning
- **GIVEN** a caller invoking `run_tasks(tasks)`
- **WHEN** the function executes
- **THEN** a `DeprecationWarning` MUST be emitted with a message referencing `IsolatedRunner` as the replacement.
