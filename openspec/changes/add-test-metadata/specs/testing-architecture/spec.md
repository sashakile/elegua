## ADDED Requirements

### Requirement: Epistemic Test Classification
The TOML test format SHALL support a `kind` field that classifies each test by its cross-backend portability expectation. The field SHALL accept one of three values: `universal`, `convention`, or `implementation`.

#### Scenario: File-level kind default
- **GIVEN** a TOML test file with `[meta]` containing `kind = "universal"`
- **WHEN** the file is loaded via `load_test_file()`
- **THEN** `TestFileMeta.kind` MUST be `"universal"`
- **AND** tests without an explicit `kind` MUST have `kind = None`; consumers SHOULD fall back to the file-level value.

#### Scenario: Per-test kind override
- **GIVEN** a TOML test file with `kind = "universal"` in `[meta]`
- **AND** a test case with `kind = "implementation"`
- **WHEN** the file is loaded
- **THEN** the test case's `kind` MUST be `"implementation"`, overriding the file default.

#### Scenario: Kind defaults to None when omitted
- **GIVEN** a TOML test file with no `kind` field in `[meta]` or `[[tests]]`
- **WHEN** the file is loaded
- **THEN** `kind` MUST be `None` on both `TestFileMeta` and `TestCase`.

#### Scenario: Invalid kind value in meta
- **GIVEN** a TOML test file with `kind = "axiom"` in `[meta]` (not in the allowed set)
- **WHEN** the file is loaded
- **THEN** `load_test_file()` MUST raise `SchemaError`.

#### Scenario: Invalid kind value in test
- **GIVEN** a TOML test file with a test case containing `kind = "axiom"`
- **WHEN** the file is loaded
- **THEN** `load_test_file()` MUST raise `SchemaError`.

### Requirement: Primary Source Reference
The TOML test format SHALL support a `source` field on `[meta]` and `[[tests]]` for tracing the test to its primary mathematical reference.

#### Scenario: File-level source
- **GIVEN** a TOML test file with `source = "DLMF 4.14.E1"` in `[meta]`
- **WHEN** the file is loaded
- **THEN** `TestFileMeta.source` MUST be `"DLMF 4.14.E1"`.

#### Scenario: Per-test source override
- **GIVEN** a test case with `source = "doi:10.1016/j.jsc.2009.06.002"`
- **WHEN** the file is loaded
- **THEN** `TestCase.source` MUST be `"doi:10.1016/j.jsc.2009.06.002"`.

#### Scenario: Source absent
- **GIVEN** a TOML test file with no `source` field
- **WHEN** the file is loaded
- **THEN** `source` MUST be `None`.

### Requirement: Validity Conditions
The TOML test format SHALL support a `conditions` field on `[meta]` and `[[tests]]` for specifying the mathematical domain under which the test's claim holds.

#### Scenario: Conditions specified
- **GIVEN** a test case with `conditions = "real x, x > 0"`
- **WHEN** the file is loaded
- **THEN** `TestCase.conditions` MUST be `"real x, x > 0"`.

#### Scenario: Conditions absent
- **GIVEN** a TOML test file with no `conditions` field
- **WHEN** the file is loaded
- **THEN** `conditions` MUST be `None`.

### Requirement: Human Review Marker
The TOML test format SHALL support a `reviewed` field on `[meta]` for recording that a human or authority has validated the test's correctness. The conventional string format is `"who:YYYY-MM-DD"` but is not structurally validated.

#### Scenario: Reviewed as boolean
- **GIVEN** a TOML test file with `reviewed = true` in `[meta]`
- **WHEN** the file is loaded
- **THEN** `TestFileMeta.reviewed` MUST be `true`.

#### Scenario: Reviewed with attribution
- **GIVEN** a TOML test file with `reviewed = "sasha:2025-07-15"` in `[meta]`
- **WHEN** the file is loaded
- **THEN** `TestFileMeta.reviewed` MUST be `"sasha:2025-07-15"`.

#### Scenario: Reviewed as false
- **GIVEN** a TOML test file with `reviewed = false` in `[meta]`
- **WHEN** the file is loaded
- **THEN** `TestFileMeta.reviewed` MUST be `false`, equivalent to absent for consumers.

#### Scenario: Reviewed absent
- **GIVEN** a TOML test file with no `reviewed` field
- **WHEN** the file is loaded
- **THEN** `TestFileMeta.reviewed` MUST be `None`.

### Requirement: Backend Scope
The TOML test format SHALL support a `backends` field on `[meta]` and `[[tests]]` for declaring which adapter IDs the test applies to. When absent, the test applies to all backends.

#### Scenario: Backends specified
- **GIVEN** a test case with `backends = ["sympy", "wolfram"]`
- **WHEN** the file is loaded
- **THEN** `TestCase.backends` MUST be `["sympy", "wolfram"]`.

#### Scenario: Backends absent means all
- **GIVEN** a TOML test file with no `backends` field
- **WHEN** the file is loaded
- **THEN** `backends` MUST be `None`, interpreted as applicable to all backends.

#### Scenario: Empty backends list
- **GIVEN** a TOML test file with `backends = []`
- **WHEN** the file is loaded
- **THEN** `load_test_file()` MUST raise `SchemaError`.
