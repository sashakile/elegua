## ADDED Requirements

### Requirement: SymPy Adapter Extra

The system SHALL provide an optional SymPy adapter (`elegua[sympy]`) that
implements the `Adapter` ABC (`src/elegua/adapter.py`) using in-process
SymPy function calls, requiring no external servers or licenses.

#### Scenario: Install and use SymPy adapter

- **GIVEN** a user installs `pip install elegua[sympy]`
- **WHEN** they import `from elegua.sympy import SympyAdapter`
- **THEN** `SympyAdapter` MUST be a valid `Adapter` subclass with `adapter_id = "sympy"`

#### Scenario: Execute an integration task

- **GIVEN** a `SympyAdapter` instance
- **WHEN** `execute()` is called with an `EleguaTask(action="Integrate", payload={"expression": "Sin[x]", "variable": "x"})`
- **THEN** it MUST return a `ValidationToken` with `status=OK`, `result["repr"]` equal to `str()` of the SymPy result expression, `result["type"]` equal to the SymPy type name, and `result["properties"]` as an empty dict

#### Scenario: Execute a differentiation task

- **GIVEN** a `SympyAdapter` instance
- **WHEN** `execute()` is called with an `EleguaTask(action="Differentiate", payload={"expression": "x**3/3", "variable": "x"})`
- **THEN** it MUST return a `ValidationToken` with `status=OK` and `result["repr"]` equal to `str()` of the SymPy result expression

#### Scenario: Unknown action returns EXECUTION_ERROR

- **GIVEN** a `SympyAdapter` instance
- **WHEN** `execute()` is called with `action="UnknownAction"`
- **THEN** it MUST return a `ValidationToken` with `status=EXECUTION_ERROR` and `metadata["error"]` describing the unsupported action

#### Scenario: SymPy computation error returns EXECUTION_ERROR

- **GIVEN** a `SympyAdapter` instance
- **WHEN** `execute()` is called with a valid expression that triggers a SymPy exception during computation (e.g., `ValueError`, `RuntimeError`)
- **THEN** it MUST return a `ValidationToken` with `status=EXECUTION_ERROR` and `metadata["error"]` containing the exception message

#### Scenario: Timeout on long-running operation

- **GIVEN** a `SympyAdapter(timeout=5.0)` instance
- **WHEN** `execute()` is called with an integrand that causes SymPy to hang
- **THEN** it MUST return a `ValidationToken` with `status=TIMEOUT` within `timeout + 2` seconds (7 seconds)

#### Scenario: Unevaluated integral flagged in metadata

- **GIVEN** a `SympyAdapter` instance
- **WHEN** `execute()` is called with an integrand that SymPy cannot solve (returns `Integral(...)`)
- **THEN** it MUST return a `ValidationToken` with `status=OK`, `result["repr"]` containing the unevaluated form, and `metadata["unevaluated"]` set to `True`

### Requirement: SymPy Expression Parsing

The `SympyAdapter` SHALL parse expression strings from task payloads using
Wolfram/Mathematica syntax as the primary format, with Python/SymPy syntax
as fallback.

#### Scenario: Parse Wolfram-syntax expression

- **GIVEN** a task payload with `expression = "Sin[x] + Cos[x]"`
- **WHEN** the adapter parses the expression
- **THEN** it MUST produce the SymPy equivalent of `sin(x) + cos(x)`

#### Scenario: Parse Wolfram-syntax exponentiation

- **GIVEN** a task payload with `expression = "x^2 + 1"`
- **WHEN** the adapter parses the expression via `parse_mathematica()`
- **THEN** it MUST produce `x**2 + 1` (power), NOT `Xor(x, 2) + 1`

#### Scenario: Fallback to Python syntax

- **GIVEN** a task payload with `expression = "sin(x) + cos(x)"`
- **WHEN** the Wolfram parser fails or is not applicable
- **THEN** the adapter MUST fall back to `parse_expr()` and produce the correct SymPy expression

#### Scenario: Explicit parse mode

- **GIVEN** a `SympyAdapter(parse_mode="python")` instance
- **WHEN** a task payload contains `expression = "x**2"`
- **THEN** it MUST use `parse_expr()` directly without attempting Wolfram parsing

#### Scenario: Unparsable expression returns EXECUTION_ERROR

- **GIVEN** a task payload with `expression = "<<<invalid>>>"`
- **WHEN** both the Wolfram parser and the Python parser fail
- **THEN** the adapter MUST return a `ValidationToken` with `status=EXECUTION_ERROR` and `metadata["error"]` describing the parse failure

### Requirement: SymPy Numeric Sample Generation

The `SympyAdapter` SHALL generate `numeric_samples` in the `ValidationToken`
result when sample points are configured on the adapter instance via the
`sample_points` constructor parameter. Sample points are evaluated using
`sympy.lambdify` with the `"numpy"` module backend.

#### Scenario: Generate samples from configured points

- **GIVEN** a `SympyAdapter(sample_points=[{"x": 0.5}, {"x": 1.0}, {"x": 2.0}])` instance
- **WHEN** the adapter executes an integration task successfully
- **THEN** `result["numeric_samples"]` MUST be a list of `{"vars": dict[str, float], "value": float}` entries, one per successfully evaluated point

#### Scenario: Skip sample points that cause domain errors

- **GIVEN** sample points that include a pole (e.g., `{"x": 0.0}` for `1/x`) or a point producing complex, nan, or inf results
- **WHEN** the adapter evaluates the result at that point
- **THEN** it MUST skip the failing point and include only valid finite real evaluations in `numeric_samples`

#### Scenario: No sample points configured

- **GIVEN** a `SympyAdapter()` instance with no `sample_points` argument
- **WHEN** the adapter executes successfully
- **THEN** the `result` MUST NOT contain a `numeric_samples` key
