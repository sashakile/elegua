# Change: Add epistemic and provenance metadata to test files

## Why

Elegua's TOML test files carry operational metadata (how to run the test) but nothing about what kind of mathematical claim the test represents, where it comes from, or whether it has been validated by a human or authority. This makes it impossible to distinguish a universal mathematical identity from a backend-specific regression test, or to cite a test case in a Computational Research Object (CRO). As the project targets cross-language validation, tests need to be classifiable, traceable to primary sources, and packageable as citable research artifacts.

## What Changes

1. **`kind` field** on `TestFileMeta` and `TestCase` --- a three-value enum (`universal`, `convention`, `implementation`) classifying the test by its portability expectation. File-level default with per-test override, following the same inheritance mechanism as `oracle_is_axiom` (per-test value is `None` when omitted; consumers fall back to file-level).

2. **`source` field** on `TestFileMeta` and `TestCase` --- free-text reference to the primary mathematical source (DLMF tag, DOI, textbook citation). Optional, no structural validation.

3. **`conditions` field** on `TestFileMeta` and `TestCase` --- free-text validity domain (e.g., `"real x"`, `"Re(s) > 1"`), following the DLMF pattern of specifying constraints under which an identity holds.

4. **`reviewed` field** on `TestFileMeta` --- human/authority sign-off marker. Either a boolean or a `"who:YYYY-MM-DD"` string. Optional, defaults to absent (unvalidated).

5. **`backends` field** on `TestFileMeta` and `TestCase` --- list of adapter IDs this test applies to. Optional, defaults to all backends. Primarily useful for `implementation`-kind tests.

All new fields are optional with sensible defaults. Existing TOML files remain valid without modification.

## Deferred

- **Validation provenance as harness output**: Recording which CAS validated a test and when is harness output, not input metadata. `ValidationToken` already captures `adapter_id` and timing. Aggregation into RO-Crate/PROV-O exports is future work.
- **Harness enforcement**: Making the pipeline *enforce* `kind` semantics (e.g., failing CI when a `universal` test doesn't pass on all backends) is a follow-on change. This proposal is metadata-only.
- **RO-Crate export**: Packaging test suites as formal Research Objects with JSON-LD is a future capability that builds on this metadata.

## Impact

- Affected specs: `testing-architecture` (TOML schema, data models)
- Affected code: `bridge.py` (parsing, dataclasses), test fixtures
- No breaking changes --- all fields optional, backward compatible
- No interaction with `refactor-composition-pipeline` or `add-sympy-adapter` (orthogonal concerns)
