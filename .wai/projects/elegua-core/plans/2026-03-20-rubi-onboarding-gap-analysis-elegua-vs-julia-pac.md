# RUBI Onboarding: Elegua vs Julia Package — Concern Split

## Context

RUBI (Rule-Based Integration) has ~73,000 integration rules originally in
Mathematica. The goal is to verify a Julia/Symbolics.jl port against the
Wolfram original using elegua as the verification orchestrator.

This is the first non-tensor domain for elegua. The foundations spec
(REQ-FOUND-001 §1) explicitly names RUBI as a motivating scenario:
> "GIVEN a new symbolic domain like RUBI is implemented, WHEN the RUBI
> adapter is registered with Eleguá, THEN it MUST be possible to execute
> RUBI verification tasks using the same Eleguá orchestrator."

---

## Concern Divide

### Elegua's responsibility (domain-agnostic orchestration)

Elegua owns the **infrastructure of trust** — the plumbing that lets any
two CAS backends be compared. It must NOT contain RUBI-specific or
Julia-specific logic in its core.

### Julia package's responsibility (domain-specific compute)

A new Julia package (e.g., `RubiOracle.jl` or `EleguaJulia.jl`) owns
the **compute backend** — accepting expressions over HTTP, evaluating
them in Symbolics.jl, and returning results in the oracle protocol format.
RUBI rule definitions, integration algorithms, and Julia-specific
isolation live here.

### Wolfram-side RUBI adapter (likely in sxAct or its own package)

The Wolfram RUBI init script (`Needs["Rubi`"]`) and RUBI-specific
expression builder are NOT elegua-core concerns. They're injected via
`ELEGUA_WOLFRAM_INIT` and the `expr_builder` callable, same as xAct.

---

## What's missing in elegua (5 gaps)

### Gap 1: `elegua[julia]` — Julia oracle extra

**Owner:** elegua
**Why:** The extension model (`pip install elegua[julia]`) is elegua's
pattern. The Julia extra provides the Python-side plumbing to talk to a
Julia oracle server, just as `elegua[wolfram]` provides wolframclient.

**What to build:**
- `src/elegua/julia/__init__.py` — package entry point
- `src/elegua/julia/adapter.py` — `JuliaOracleAdapter(Adapter)` that
  wraps `OracleClient` with a Julia-specific `expr_builder` injection
  point. Mirrors `WolframOracleAdapter` but for Julia expression syntax.
- `src/elegua/julia/__main__.py` — CLI entry point (`python -m elegua.julia serve`)

**What NOT to build here:**
- The Julia HTTP server itself (that's the Julia package)
- The Julia kernel manager (that's the Julia package)
- Any RUBI-specific logic

**Key design question:** Should `elegua[julia]` include a Python-side
`KernelManager` that spawns/manages a Julia process (like wolfram's
`KernelManager` wraps `WolframLanguageSession`)? Or should it expect an
already-running Julia server and just provide the adapter?

**Recommendation:** Just the adapter + CLI launcher. The Julia package
manages its own process. Elegua provides a thin `JuliaOracleAdapter`
and optionally a subprocess launcher (`elegua julia serve` shells out to
`julia -e 'using EleguaJulia; serve()'`).

### Gap 2: Numeric comparison layer (L4)

**Owner:** elegua-core
**Why:** This is domain-agnostic infrastructure. Any symbolic verification
benefits from "evaluate both sides at random points and check they agree."
RUBI needs it acutely (different CAS produce structurally different but
mathematically equal antiderivatives), but tensor verification needs it
too (the papers repo describes this for Bianchi identity verification).

**What to build:**
- `src/elegua/compare_numeric.py` — a `LayerFn` that:
  1. Extracts `result["repr"]` from both tokens
  2. Evaluates both expressions at N random points (configurable)
  3. Returns `OK` if all evaluations agree within tolerance
  4. Returns `MATH_MISMATCH` otherwise
- Register as L4 in the pipeline: `pipeline.register(4, "numeric", compare_numeric)`
- Support configurable: variable names, sampling range, tolerance, N samples

**What NOT to build here:**
- CAS-specific evaluation (the numeric sampling itself needs a compute
  backend — this layer calls back to the oracle or uses a lightweight
  evaluator like `sympy` or `math`)
- Domain-specific normalization (that's L3)

**Key design question:** How does L4 evaluate expressions numerically?
Options:
1. **Callback to oracle** — send `N[expr /. x -> 0.5]` to the oracle
   (requires oracle round-trip, slow but accurate)
2. **Embedded lightweight evaluator** — parse repr into sympy, evaluate
   with `float()` (fast but limited to expressions sympy can parse)
3. **Pre-computed numeric values** — require adapters to return
   `result["numeric_samples"]` alongside `result["repr"]`

**Recommendation:** Option 3. Extend the adapter contract so that
adapters MAY include `result["numeric_samples"]: list[{vars: dict, value: float}]`
in the ValidationToken. The L4 comparator checks if sample values agree.
This keeps L4 stateless and oracle-free.

### Gap 3: Canonical normalization layer (L3)

**Owner:** elegua-core (plugin interface) + domain packages (implementations)
**Why:** `x^2/2` and `(1/2)*x^2` are identical math but different strings.
L1/L2 reject them. L3 normalizes before comparing. The plugin interface
is elegua's job; the actual normalization rules are domain-specific.

**What to build:**
- Document the `LayerFn` contract for L3 normalizers
- Provide a `NormalizerRegistry` (or just use `pipeline.register()` as-is)
- Optionally: a simple canonical-form normalizer that handles common
  algebraic equivalences (coefficient ordering, sign normalization)

**What NOT to build here:**
- RUBI-specific normalization (e.g., `+C` constant handling)
- CAS-specific expression parsing

**Note:** This may not be needed for MVP if L4 numeric comparison is
robust enough. L3 is an optimization to catch matches faster.

### Gap 4: Expression interchange (result format)

**Owner:** elegua-core (contract definition)
**Why:** `result["repr"]` is currently a plain string whose format varies
by CAS. Wolfram returns `T[-a,-b]`, Julia might return `T[a,b]` or
`T_{a,b}`. Without a shared format, even L2 structural comparison fails.

**What to build:**
- Define a recommended `result` schema in the spec:
  ```
  result.repr: str           # CAS-native string (for display)
  result.canonical: str      # Optional: normalized form (for L3)
  result.numeric_samples: [] # Optional: evaluated points (for L4)
  result.type: str           # Expression type
  result.properties: dict    # Computed properties
  ```
- Adapters SHOULD populate `canonical` using a shared format (e.g.,
  prefix S-expressions, or a minimal agreed-upon normalization)
- L2 structural comparison SHOULD prefer `canonical` over `repr` when
  available

**What NOT to build here:**
- A universal CAS interchange format (that's Chacana's long-term goal)
- CAS-specific parsers

### Gap 5: RUBI test suite format

**Owner:** elegua-core (format support) + RUBI project (test data)
**Why:** The TOML test format is generic (`action` + `payload` dict) but
all existing test files use xAct actions. Need to validate the format
works cleanly for integration-domain actions.

**What to build:**
- Example RUBI test files in TOML demonstrating the action vocabulary:
  ```toml
  [[tests]]
  id = "rubi-rule-1.1.1"

  [[tests.operations]]
  action = "Integrate"
  [tests.operations.args]
  expression = "x^2"
  variable = "x"

  [tests.expected]
  expr = "x^3/3"
  ```
- Verify the bridge loader, IsolatedRunner, and verdict evaluator handle
  integration-domain actions without modification
- Add derivative-check as a verdict mode: `expected.derivative_check = true`
  means "differentiate result w.r.t. variable and compare to integrand"

**What NOT to build here:**
- The 73k RUBI rules as TOML (that's a data generation task)
- RUBI-specific test runner logic

---

## What belongs in the Julia package (NOT elegua)

For clarity, these are explicitly out of scope for elegua:

| Component | Owner | Description |
|-----------|-------|-------------|
| Julia HTTP server | `EleguaJulia.jl` | HTTP.jl server implementing oracle protocol endpoints |
| Julia kernel manager | `EleguaJulia.jl` | Session lifecycle, init script loading, cleanup |
| Julia context isolation | `EleguaJulia.jl` | Module-based or workspace-scoped isolation |
| Symbolics.jl evaluation | `EleguaJulia.jl` | `Symbolics.integrate()`, `Symbolics.derivative()`, etc. |
| RUBI rule definitions | `Rubi.jl` or similar | The actual 73k integration rules in Julia |
| RUBI Wolfram init script | sxAct or RUBI project | `Needs["Rubi`"]` loading for Wolfram oracle |
| RUBI expression builders | RUBI project | `(action, payload) -> CAS expression` for both sides |
| RUBI test data | RUBI project | The 73k rules as TOML test files |

---

## Implementation order (elegua only)

### Phase 1: Validate the adapter pattern works for non-Wolfram

1. Create `src/elegua/julia/` package with `JuliaOracleAdapter`
2. Write unit tests using `EchoOracle` (no real Julia needed)
3. Add `elegua[julia]` optional dependency in `pyproject.toml`
4. Verify MultiTierRunner works with two different adapter types

### Phase 2: Numeric comparison (L4)

1. Define `result.numeric_samples` schema in the spec
2. Implement `compare_numeric` LayerFn
3. Test with synthetic tokens (known-equal and known-different expressions)
4. Register in default pipeline as L4

### Phase 3: Result format and interchange

1. Extend ValidationToken result schema docs with `canonical`, `numeric_samples`
2. Update L2 structural comparison to prefer `canonical` when present
3. Write adapter guidelines: "what adapters SHOULD return"

### Phase 4: RUBI test format validation

1. Create example RUBI TOML test files
2. Add `derivative_check` verdict mode
3. End-to-end test: TOML -> bridge -> runner -> verdict (with EchoOracle)

### Phase 5: Integration testing with real Julia

1. Docker-compose with Julia + Symbolics.jl oracle server
2. Record snapshots from both Wolfram RUBI and Julia RUBI
3. MultiTier verification: Wolfram vs Julia via snapshot replay
