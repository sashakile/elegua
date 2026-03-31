## 1. Tests (TDD --- write failing tests first)

- [ ] 1.1 Test: `kind` parsed from `[meta]`, defaults to `None` when absent
- [ ] 1.2 Test: `kind` parsed per-test, defaults to `None` when absent
- [ ] 1.3 Test: invalid `kind` in `[meta]` raises `SchemaError`
- [ ] 1.4 Test: invalid `kind` in `[[tests]]` raises `SchemaError`
- [ ] 1.5 Test: `source` parsed from `[meta]` and per-test
- [ ] 1.6 Test: `conditions` parsed from `[meta]` and per-test
- [ ] 1.7 Test: `reviewed` parsed as `bool` and as `str`; `false` is equivalent to absent
- [ ] 1.8 Test: `backends` parsed as list of strings
- [ ] 1.9 Test: empty `backends = []` raises `SchemaError`
- [ ] 1.10 Test: all new fields default to `None` when omitted (backward compatibility)

## 2. Data Models

- [ ] 2.1 Add `kind`, `source`, `conditions`, `reviewed`, `backends` fields to `TestFileMeta` dataclass in `bridge.py`
- [ ] 2.2 Add `kind`, `source`, `conditions`, `backends` fields to `TestCase` dataclass in `bridge.py`
- [ ] 2.3 Define `VALID_KINDS = {"universal", "convention", "implementation"}` constant

## 3. Parsing

- [ ] 3.1 Update `load_test_file()` to parse new `[meta]` fields (`kind`, `source`, `conditions`, `reviewed`, `backends`)
- [ ] 3.2 Update `_parse_test()` to parse new per-test fields (`kind`, `source`, `conditions`, `backends`)
- [ ] 3.3 Add `SchemaError` validation for invalid `kind` values
- [ ] 3.4 Add `SchemaError` validation for empty `backends` list

## 4. Fixtures

- [ ] 4.1 Add a `universal`-kind fixture TOML file demonstrating the metadata fields
- [ ] 4.2 Add an `implementation`-kind fixture TOML file with `backends` scoping

## 5. Spec Update

- [ ] 5.1 Update `testing-architecture` spec section 3.1 (Complete Schema) with new fields
- [ ] 5.2 Update `testing-architecture` spec section 3.2 (Data Models) table with new fields

## 6. Documentation

- [ ] 6.1 Update docstring on `TestFileMeta` to describe new fields
- [ ] 6.2 Update docstring on `TestCase` to describe new fields
