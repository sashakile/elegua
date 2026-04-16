## MODIFIED Requirements

### Requirement: Verdict Evaluation
The architecture SHALL evaluate test results against expected outcomes defined in the test file, producing a `Verdict` with status `pass`, `fail`, `skip`, or `error`. Additionally, `Verdict` SHALL provide a `from_comparison()` class method to bridge `ComparisonResult` into the verdict system.

#### Scenario: Expression match
- **GIVEN** a test case with `expected.expr = "x^2"`
- **WHEN** the last operation produces a token with `result.repr = "x^2"`
- **THEN** the verdict MUST be `pass`.

#### Scenario: Expression mismatch
- **GIVEN** a test case with `expected.expr = "x^2"`
- **WHEN** the last operation produces a token with `result.repr = "x^3"`
- **THEN** the verdict MUST be `fail` with actual and expected values in the message.

#### Scenario: Expected error
- **GIVEN** a test case with `expected.expect_error = true`
- **WHEN** the operation raises an operational error
- **THEN** the verdict MUST be `pass`.

#### Scenario: No expected block means pass
- **GIVEN** a test case with no `[tests.expected]` section
- **WHEN** execution completes without error
- **THEN** the verdict MUST be `pass` (execution-only test).

#### Scenario: Normalizer-based comparison
- **GIVEN** a caller-injected normalizer function
- **WHEN** `expected.expr` or `expected.normalized` is checked
- **THEN** both actual and expected values MUST be normalized before comparison.

#### Scenario: Bridge from ComparisonResult (OK)
- **GIVEN** a `ComparisonResult` with `status=TaskStatus.OK` and `layer=1`
- **WHEN** `Verdict.from_comparison(result)` is called
- **THEN** the returned `Verdict` MUST have `status="pass"`.

#### Scenario: Bridge from ComparisonResult (MATH_MISMATCH)
- **GIVEN** a `ComparisonResult` with `status=TaskStatus.MATH_MISMATCH` and `layer=2`
- **WHEN** `Verdict.from_comparison(result)` is called
- **THEN** the returned `Verdict` MUST have `status="fail"` and a message indicating the mismatch layer.
