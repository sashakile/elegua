## Context

Eleguá's Layer 2 property-based testing validates mathematical laws (e.g., "for all tensors T, symmetrize(symmetrize(T)) == symmetrize(T)") by generating random inputs and checking the law holds. The current `PropertyRunner` does this with a hand-rolled sample loop and PCG64 RNG. It works for simple cases but cannot shrink failing inputs, compose generators, or remember past failures.

Hypothesis is the standard Python PBT library (>10 years, >5k GitHub stars, used by NumPy, pandas, CPython). It provides shrinking, composable strategies, an example database, stateful testing, and health checks.

### Stakeholders
- Elegua core consumers (sxAct, future RUBI project)
- Test authors writing property specs in TOML

### Constraints
- TOML property spec format must remain the primary authoring interface
- PCG64 cross-platform sampling for L4 numeric comparison must be untouched
- `hypothesis` becomes a core dependency (not optional) since PBT is a core capability

## Goals / Non-Goals

**Goals:**
- Full shrinking: failing inputs are automatically reduced to minimal counterexamples
- Composable strategies: type names in TOML map to Hypothesis strategies that can be composed
- Example database: past failures are persisted and replayed first on subsequent runs
- Configurable settings: max examples, deadline, database path via TOML or Python API
- Backward-compatible TOML format: existing property TOMLs continue to work

**Non-Goals:**
- Stateful testing in TOML (Python API only — TOML is for "for all X, P(X)" properties)
- Replacing L4 numeric comparison (PCG64 stays for cross-CAS sampling)
- Hypothesis profiles or CI-specific settings (users configure via `hypothesis.settings`)

## Decisions

### Decision 1: Hypothesis strategies replace GeneratorRegistry

**What:** TOML `type` field maps to a Hypothesis strategy instead of a `Callable[[Generator], Any]`.

**Why:** Strategies compose (via `st.one_of`, `st.builds`, `st.flatmap`), support shrinking natively, and integrate with Hypothesis health checks. Raw callables cannot shrink because Hypothesis doesn't know their structure.

**New API:**
```python
from elegua.property import StrategyRegistry
from hypothesis import strategies as st

registry = StrategyRegistry()
registry.register("integer", st.integers(-1000, 1000))
registry.register("positive_real", st.floats(min_value=0.01, max_value=1e6))
registry.register("rank2_tensor", st.builds(make_rank2, dim=st.integers(2, 6)))
```

**Alternatives considered:**
- Wrapping existing callables in `st.composite`: possible but loses shrinking quality since Hypothesis can't introspect the wrapped function's structure.
- Making Hypothesis optional: rejected because shrinking is the whole point, and a PBT library without shrinking is just a fuzzer.

### Decision 2: PropertyRunner delegates to `hypothesis.given`

**What:** `PropertyRunner.run()` constructs a `@given`-decorated test function from the spec and executes it.

**Why:** This gives us shrinking, example database, health checks, and settings for free. The runner translates TOML specs into Hypothesis test functions at runtime.

**How it works:**
1. Parse `PropertySpec` from TOML (unchanged)
2. Look up strategies from `StrategyRegistry` for each generator
3. Build a `@given(**strategies)` test function that calls the evaluator
4. Execute via `hypothesis.find` or a wrapped `@given` call
5. Catch `hypothesis.errors.Falsifying` and convert to `PropertyResult` with shrunk `Failure`

### Decision 3: TOML format extended with optional strategy parameters

**What:** Generator entries in TOML can include an optional `params` table for strategy configuration.

```toml
[[generators]]
name = "$x"
type = "integer"
[generators.params]
min_value = -1000
max_value = 1000
```

**Why:** Lets test authors constrain inputs without writing Python code. The `params` dict is passed as kwargs to the strategy factory if the registry entry is a callable, or ignored if it's a pre-built strategy.

**Backward compatibility:** `params` is optional. Existing TOMLs without it work unchanged.

### Decision 4: Settings configurable via TOML and Python

**What:** Property specs can include a `[settings]` table:
```toml
[settings]
max_examples = 200
deadline = 5000  # ms
database_path = ".hypothesis/db"
```

**Why:** Test authors need to tune PBT parameters per property (e.g., expensive oracle calls need fewer examples with a longer deadline).

**Default:** 100 examples, 1000ms deadline, project-level `.hypothesis/` database.

### Decision 5: PCG64 sampling stays for L4

**What:** `compare_numeric.py` and its PCG64-based sample point generation are completely untouched.

**Why:** L4 numeric comparison requires *both* CAS backends to evaluate at identical points. This is a cross-platform determinism requirement that Hypothesis cannot satisfy (its RNG is Python-internal and shrinking changes the sequence). PCG64 is the right tool for this job.

## Risks / Trade-offs

- **New core dependency**: `hypothesis` adds ~2MB and pulls in `sortedcontainers`. Acceptable for a core PBT capability.
- **Slower first run**: Hypothesis explores more input space than the current flat loop. Mitigated by `max_examples` setting.
- **Seed reproducibility changes**: The current `seed` parameter for exact PCG64 reproduction goes away for PBT (Hypothesis uses its own database instead). Users who need exact reproduction use `@reproduce_failure` decorators or the example database. This is a deliberate trade: shrinking quality > exact seed control.
- **Learning curve**: Test authors used to `GeneratorRegistry` callables must learn `hypothesis.strategies`. Mitigated by providing common built-in strategies and clear docs.

## Migration Plan

1. Add `hypothesis` to core dependencies in `pyproject.toml`
2. Implement `StrategyRegistry` with same `register(name, strategy)` API
3. Implement `HypothesisPropertyRunner` delegating to `@given`
4. Keep `GeneratorRegistry` as deprecated alias (wraps callables in `st.builds`)
5. Update `PropertyResult` / `Failure` to include shrunk counterexamples
6. Update tests
7. Update spec

**Rollback:** Revert to previous `PropertyRunner` — no data migration needed since the TOML format is backward-compatible.

## Open Questions

None — the design is straightforward delegation to Hypothesis.
