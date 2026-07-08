# RUBI Onboarding: Elegua vs Julia Package — Concern Split

## Context

RUBI (Rule-Based Integration) has thousands of integration rules
originally in Mathematica. The goal is to verify a Julia/Symbolics.jl
port against the Wolfram original using elegua as the verification
orchestrator.

This is the first non-tensor domain for elegua. The foundations spec
(REQ-FOUND-001 §1) explicitly names RUBI as a motivating scenario:
> "GIVEN a new symbolic domain like RUBI is implemented, WHEN the RUBI
> adapter is registered with Eleguá, THEN it MUST be possible to execute
> RUBI verification tasks using the same Eleguá orchestrator."

---

## Concern Divide

**Litmus test:** If removing the code breaks only one domain, it belongs
in that domain's package. If it breaks all domains, it belongs in elegua.

### Elegua (domain-agnostic orchestration)

Elegua owns the **infrastructure of trust** — adapter lifecycle,
comparison pipeline, test format, snapshot replay. It must NOT contain
RUBI-specific or Julia-specific logic.

### Julia package (domain-specific compute)

A new Julia package (e.g., `EleguaJulia.jl`) owns the **compute
backend** — HTTP server, expression evaluation in Symbolics.jl, context
isolation, cleanup. RUBI rule definitions and Julia-specific process
management live here.

### RUBI project (domain-specific test data + expression builders)

The Wolfram RUBI init script (`Needs["Rubi`"]`), Julia-side RUBI rules,
expression builders for both sides, and the test suite (TOML files) are
NOT elegua concerns. They're injected via `ELEGUA_WOLFRAM_INIT` and the
`expr_builder` callable, same as xAct today.

---

## Validation: the adapter is already generic

The review identified that `OracleAdapter` (formerly `WolframOracleAdapter`)
is backend-agnostic — it wraps `OracleClient` (stdlib HTTP) with an
injectable `expr_builder`. Integration tests already prove this: the
echo oracle (a Python HTTP server with no Wolfram) works with the same
adapter.

**Done:** Renamed `WolframOracleAdapter` → `OracleAdapter` with backward-
compat alias. Renamed `load_sxact_toml` → `load_test_file`. Updated
docstrings to remove domain-specific language.

**Consequence:** No `elegua[julia]` adapter package is needed. A Julia
oracle server that implements the HTTP protocol works out of the box:
```python
adapter = OracleAdapter(
    oracle=OracleClient("http://localhost:9000"),
    expr_builder=rubi_julia_builder,
)
```

---

## What's missing in elegua (3 gaps)

### Gap 1: Numeric comparison layer (L4)

**Owner:** elegua-core
**Why:** Different CAS produce structurally different but mathematically
equal results. `x^2/2` vs `(1/2)*x^2` fail L1/L2. For RUBI this is
the norm — antiderivatives have many equivalent forms. Tensor
verification needs this too (Bianchi identity, per the papers repo).

**What to build:**
- `src/elegua/compare_numeric.py` — a comparison function that checks
  whether pre-computed numeric samples from both tokens agree within
  tolerance.

**Design decision: how does L4 get numeric values?**

Adapters include sample values in the result dict. This keeps L4
stateless and oracle-free:
```python
result["numeric_samples"] = [
    {"vars": {"x": 0.5}, "value": 0.125},
    {"vars": {"x": 1.0}, "value": 0.5},
    ...
]
```

The **sample points are prescribed by the test payload**, not chosen by
adapters independently. This solves the coordination problem — both
adapters evaluate at the same points:
```toml
[tests.expected]
sample_points = [{x = 0.5}, {x = 1.0}, {x = 2.0}]
```

**API issue:** The current `LayerFn` signature is
`(ValidationToken, ValidationToken) -> TaskStatus` — no way to pass
config (tolerance, min samples). Fix: use a closure that captures config:
```python
def make_numeric_comparator(tol: float = 1e-10, min_samples: int = 3) -> LayerFn:
    def compare(a: ValidationToken, b: ValidationToken) -> TaskStatus:
        ...
    return compare
```

This preserves the existing `pipeline.register()` API. No pipeline
changes needed.

**Acceptance criteria:**
- Synthetic test: two tokens with matching samples → OK
- Synthetic test: two tokens with divergent samples → MATH_MISMATCH
- Synthetic test: tokens with no/insufficient samples → MATH_MISMATCH
- Registered as L4, runs after L1/L2 in default pipeline

### Gap 2: Result schema extension

**Owner:** elegua-core (contract definition)
**Why:** `result["repr"]` is a plain string whose format varies by CAS.
Without additional fields, L2 structural comparison fails across CAS
boundaries. This schema extension is required by Gap 1 (L4 needs
`numeric_samples`) and benefits all cross-CAS verification.

**What to build:**
- Document the extended result schema in the spec:
  ```
  result.repr: str               # CAS-native string (for display)
  result.type: str               # Expression type
  result.properties: dict        # Computed properties
  result.numeric_samples: list   # Optional: [{vars: dict, value: float}]
  ```
- Update L2 structural comparison to ignore `numeric_samples` (it's L4
  data, not structural).
- Write adapter guidelines: "what adapters SHOULD return for cross-CAS
  verification."

**Note on L3 (canonical normalization):** Deferred. If L4 numeric
comparison is robust, L3 is an optimization, not a requirement. The
`pipeline.register()` API already supports plugging in an L3 when
domain packages provide one.

**Acceptance criteria:**
- Spec updated with result schema
- L2 ignores numeric_samples field
- Adapter guidelines doc written

### Gap 3: Derivative-check as a property test

**Owner:** elegua-core (property testing framework)
**Why:** The gold-standard RUBI verification is `d/dx[F(x)] == f(x)` —
differentiate the antiderivative and check it matches the integrand.

This is NOT a verdict mode (verdicts are pure string comparison with no
CAS access). It's a **property test**: "for all integration results,
the derivative of the result equals the integrand."

**What to build:**
- A `PropertySpec` template for derivative-check:
  ```python
  PropertySpec(
      name="derivative_check",
      law="D[result, var] == integrand",
      generators=[...],
  )
  ```
- The property runner already supports custom evaluation functions.
  The derivative check sends `D[F, x]` to the oracle and compares with
  `f(x)` — this is an oracle-callback property test.
- Alternatively: express as a two-operation test in TOML:
  ```toml
  [[tests.operations]]
  action = "Integrate"
  [tests.operations.args]
  expression = "x^2"
  variable = "x"
  store_as = "antideriv"

  [[tests.operations]]
  action = "Differentiate"
  [tests.operations.args]
  expression = "$antideriv"
  variable = "x"

  [tests.expected]
  expr = "x^2"
  ```
  This works TODAY with no code changes — the bridge, runner, and
  verdict evaluator handle it. The `store_as` + `$ref` mechanism
  chains operations.

**Decision:** The TOML two-operation approach works without new code.
Document it as a pattern. The PropertySpec approach is future work for
batch verification of all rules.

**Acceptance criteria:**
- Example TOML test file demonstrating integrate-then-differentiate
- Verify it runs end-to-end with EchoOracle (no real CAS)
- Document the pattern in adapter guidelines

---

## What belongs in the Julia package (NOT elegua)

| Component | Owner | Description |
|-----------|-------|-------------|
| Julia HTTP server | `EleguaJulia.jl` | HTTP.jl server implementing oracle protocol |
| Julia process lifecycle | `EleguaJulia.jl` | Session start/stop, init scripts, cleanup |
| Julia context isolation | `EleguaJulia.jl` | Module-based or workspace-scoped isolation |
| Symbolics.jl evaluation | `EleguaJulia.jl` | `integrate()`, `derivative()`, etc. |
| RUBI rule definitions | `Rubi.jl` or similar | Integration rules in Julia |
| RUBI Wolfram init script | RUBI project | `Needs["Rubi`"]` for Wolfram oracle |
| RUBI expression builders | RUBI project | `(action, payload) -> expr` for both sides |
| RUBI test data | RUBI project | Integration rules as TOML test files |
| Sample point generation | RUBI project | Domain-aware point selection avoiding poles |

---

## Implementation order (elegua only)

### MVP: One RUBI rule verified end-to-end

The smallest proof that the architecture works for RUBI:
1. One TOML test file with `Integrate` + `Differentiate` operations
2. Run against EchoOracle to prove the pipeline works
3. (Later) Run against real Wolfram RUBI + Julia RUBI via snapshots

### Phase 1: Result schema + L4 numeric comparison

1. Update spec with extended result schema (Gap 2)
2. Implement `make_numeric_comparator()` closure factory (Gap 1)
3. Test with synthetic tokens
4. Register in pipeline as L4

**Done when:** `pipeline.compare(token_a, token_b)` returns OK for
tokens with different `repr` but matching `numeric_samples`.

### Phase 2: RUBI test format validation

1. Create example RUBI TOML test files (integrate + differentiate pattern)
2. Run end-to-end: TOML → bridge → IsolatedRunner → verdict (with EchoOracle)
3. Document the pattern (Gap 3)

**Done when:** `pytest tests/test_rubi_format.py` passes with at least
3 example RUBI rules in TOML format.

### Phase 3: Cross-CAS integration testing

1. Docker-compose with Julia oracle server (depends on EleguaJulia.jl)
2. Record snapshots from both Wolfram RUBI and Julia RUBI
3. MultiTierRunner verification: Wolfram vs Julia via snapshot replay
4. L4 numeric comparison catches equivalent-but-different antiderivatives

**Done when:** MultiTierRunner reports OK for at least 10 RUBI rules
where Wolfram and Julia produce structurally different but numerically
equal results.

---

## Notes

- **MultiTierRunner strict zip** (multitier.py:82): If oracle and IUT
  produce different test counts (e.g., one skips a rule), the strict
  zip will crash. May need relaxation for cross-CAS testing — track as
  a future issue if it arises.
- **L3 canonical normalization**: Deferred. The pipeline already supports
  `register(3, "canonical", fn)`. Domain packages can provide L3
  implementations when needed.
- **adapter_id for Julia**: When using OracleAdapter against a Julia
  server, the `adapter_id` defaults to `"wolfram-oracle"`. Override via
  subclass or make it configurable — minor issue, address when
  EleguaJulia.jl integration starts.
