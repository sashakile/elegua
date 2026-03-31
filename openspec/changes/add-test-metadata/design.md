## Context

Elegua is a cross-language mathematical validation harness. Its test files define mathematical claims that are evaluated across multiple CAS backends. For these test files to function as citable Computational Research Objects (CROs), they need metadata describing what kind of mathematical claim each test represents, where it comes from, and whether it has been validated.

An investigation of external standards (PROV-O, RO-Crate, DLMF, Rubi, OEIS, Lean/Mathlib, OpenMath) and a Rule-of-5 review of the initial design surfaced key architectural decisions documented here.

## Goals / Non-Goals

- **Goals**: Add static, authoring-time metadata to TOML test files that classifies, traces, and enables citability of mathematical test cases.
- **Non-Goals**: Runtime validation provenance (who ran what, when), harness enforcement of `kind` semantics, full RO-Crate packaging.

## Decisions

### Decision 1: Static metadata vs dynamic provenance

Authoring-time metadata (what kind of claim, where it comes from) and runtime provenance (which CAS validated it, when) have fundamentally different lifecycles. The first is set once by a human and changes rarely. The second grows with every test run and is naturally produced by the harness.

- **Static metadata** lives in source TOML files: `kind`, `source`, `conditions`, `reviewed`, `backends`.
- **Dynamic provenance** is harness output: `ValidationToken` already captures `adapter_id`, `status`, `metadata` (timing). Future work aggregates these into exportable provenance records.

Embedding `[[meta.validations]]` arrays in source TOML (as initially proposed) was rejected because: (a) CI would need to modify source files and commit, creating merge conflicts; (b) it mixes source with output; (c) nobody will maintain it manually.

**Standards alignment**: PROV-O vocabulary (`wasGeneratedBy`, `wasAttributedTo`, `hadPrimarySource`) applies to the harness output layer, not the TOML input layer. RO-Crate's `CreateAction` pattern maps to `ValidationToken` records, not to hand-written entries.

### Decision 2: Three-value `kind` taxonomy

The initial six-value taxonomy (axiom/theorem/identity/convention/implementation/regression) mixed mathematical epistemology with software engineering concerns. The Lean/Mathlib kernel treats `theorem` and `lemma` as identical; the DLMF doesn't distinguish identities from theorems. What matters for a cross-language harness is **portability expectation**.

| Kind | Meaning | Intended future pipeline behavior |
|------|---------|-----------------------------------|
| `universal` | Must hold on all conforming backends | Failure on any backend = bug |
| `convention` | Valid but backend-dependent (branch cuts, simplification choices) | Divergence is expected, logged |
| `implementation` | Specific to one backend's behavior (precision, internal repr, regressions) | Only run on declared backends |

> **Note**: The third column describes intended future enforcement behavior. This change delivers metadata only; enforcement is a follow-on change.

**Decision tree**:
1. Does the test express a mathematical truth independent of computation method?
   - No -> `implementation`
2. Does the truth require assumptions about computational conventions (branch cuts, canonical forms)?
   - Yes -> `convention`
   - No -> `universal` (if the truth holds only within a restricted mathematical domain, set `kind = "universal"` and specify `conditions` — e.g., `conditions = "x in [-1, 1]"`)

Mathematical sub-classifications (axiom vs theorem vs identity) can be expressed via `tags` if needed. The `kind` field carries operational semantics; `tags` carry descriptive semantics. The `conditions` field narrows the domain of a `universal` claim but does not change its kind — a domain-restricted universal truth is still universal within that domain.

### Decision 3: `source` as free text, not structured

The initial design proposed nested `[meta.source]` with `reference`, `doi`, and `url` sub-fields. This was simplified because:

- Most mathematical references don't have DOIs (textbook citations, DLMF tags, OEIS A-numbers)
- A single free-text field handles all formats: `"DLMF 4.14.E1"`, `"doi:10.1016/..."`, `"Gradshteyn & Ryzhik 7th ed., section 2.01"`, `"OEIS A000045"`
- Structured parsing can be added later if a concrete consumer needs it
- Follows OEIS's approach: human-readable references with minimal structure

### Decision 4: `conditions` follows DLMF pattern

DLMF annotates each equation with validity constraints (e.g., `"Re(s) > 1"`, `"x in [-1, 1]"`). This is the most useful metadata for cross-backend divergence: `sin(arcsin(x)) = x` is `universal` when `conditions = "x in [-1, 1]"` but `convention` outside that domain.

Free-text for now. If a structured constraint language becomes necessary, it can be parsed from the same field.

### Decision 5: `reviewed` is a simple marker, not a provenance log

A human review is a discrete event, not a growing log. The `reviewed` field is either:
- Absent/false: unvalidated
- `true`: validated but no attribution
- `"who:YYYY-MM-DD"`: attributed validation

This is intentionally minimal. Full review provenance (multiple reviewers, review comments, approval chains) is a workflow concern, not a test metadata concern.

### Decision 6: `oracle_is_axiom` remains orthogonal

`oracle_is_axiom` is an **operational flag**: "skip oracle comparison, trust the expected value." `kind` is **descriptive metadata**: "what category of claim is this." They correlate (e.g., `universal` tests with well-known expected values often set `oracle_is_axiom = true`) but neither implies the other. A `convention` test might still use the oracle for comparison; a `universal` test might skip the oracle if the expected value is definitional.

## Risks / Trade-offs

- **Risk**: `kind` taxonomy is too coarse for some use cases. **Mitigation**: `tags` provide arbitrary descriptive classification; `kind` is deliberately minimal and operationally meaningful.
- **Risk**: `source` free text is too unstructured for automated citation generation. **Mitigation**: Structured citation is a future RO-Crate export concern; the free-text field provides human-readable traceability now.
- **Risk**: `reviewed` without enforcement is toothless. **Mitigation**: This is metadata, not policy. Enforcement (e.g., CI requiring `reviewed = true` for `universal` tests) is a follow-on concern.

## Open Questions

None. All design decisions are grounded in the standards investigation and Rule-of-5 review.
