## Context

SymPy is a pure Python CAS with broad symbolic capabilities. Unlike the
Wolfram backend (HTTP + Docker + kernel lifecycle), SymPy runs in-process
with zero external infrastructure. This makes it a suitable second adapter
to prove elegua's domain agnosticism.

Primary use cases:
1. **RUBI verification IUT**: Run integration rules through SymPy and compare
   against pre-computed Wolfram oracle results
2. **Free oracle fallback**: When Wolfram is unavailable, SymPy provides
   reduced-confidence verification with no license cost
3. **Tensor cross-validation**: `sympy.tensor` implements Butler-Portugal
   canonicalization — a third independent implementation alongside Wolfram/xAct
   and Julia/XCore.jl

## Goals / Non-Goals

**Goals:**
- In-process adapter with no external dependencies beyond SymPy itself
- Action dispatch for common CAS operations (integrate, diff, simplify, etc.)
- Numeric sample generation via `lambdify` when `sample_points` are provided in the task payload
- Timeout handling for operations that can hang (SymPy integration is unbounded)
- Wolfram-syntax expression parsing for reuse of existing TOML test files

**Non-Goals:**
- Supporting every SymPy submodule (start with calculus + basic algebra)
- Performance parity with Wolfram (SymPy is known to be slower)
- Replacing the Wolfram oracle (SymPy produces silently wrong results in edge cases)
- RUBI rule loading (`rubi_integrate()` support is deferred — loading takes ~10min)
- Multi-variable integration (single-variable only for MVP)
- Wolfram-format output via `mathematica_code()` (deferred — lossy and not needed for IUT role)

## Decisions

### Action dispatch pattern

The adapter maps `task.action` strings to SymPy functions via a registry dict.
The action handler protocol is `Callable[[sympy.Expr, dict[str, Any]], sympy.Expr]`:

```python
ActionHandler = Callable[[sympy.Expr, dict[str, Any]], sympy.Expr]

_ACTIONS: dict[str, ActionHandler] = {
    "Integrate": lambda expr, payload: sympy.integrate(expr, _var(payload)),
    "Differentiate": lambda expr, payload: sympy.diff(expr, _var(payload)),
    "Simplify": lambda expr, payload: sympy.simplify(expr),
    "Solve": lambda expr, payload: sympy.solve(expr, _var(payload)),
    "Series": lambda expr, payload: sympy.series(expr, _var(payload), n=payload.get("n", 6)),
    "Limit": lambda expr, payload: sympy.limit(expr, _var(payload), _point(payload)),
}
```

Unknown actions return `EXECUTION_ERROR`. Missing required fields (e.g.,
`variable`, `point` for Limit) are caught by the `_var()` / `_point()`
helpers which raise `KeyError`, mapped to `EXECUTION_ERROR` by the adapter's
top-level error handler (same pattern as `OracleAdapter.execute()` in
`src/elegua/wolfram/adapter.py:100-112`).

SymPy exceptions during computation (e.g., `ValueError`, `RuntimeError`) are
also caught and mapped to `EXECUTION_ERROR` with the exception message in
`metadata["error"]`.

This is extensible — downstream projects can subclass and add domain-specific
actions (e.g., `DefTensor` for `sympy.tensor`).

**Alternatives considered:**
- Plugin registry with entry points: Over-engineered for the initial scope.
  Can add later if multiple SymPy action sets emerge.
- Separate adapters per domain (SympyCalculusAdapter, SympyTensorAdapter):
  Premature — one adapter with a configurable action registry is sufficient.

### Expression parsing

Task payloads contain expression strings. SymPy provides two parsers:
- `sympy.parsing.sympy_parser.parse_expr(s)` — parses Python/SymPy syntax
- `sympy.parsing.mathematica.parse_mathematica(s)` — parses Wolfram syntax

The adapter SHALL attempt `parse_mathematica()` first (since TOML test files
use Wolfram notation like `Sin[x]`, `Power[x, 2]`), falling back to
`parse_expr()` for Python notation. A `parse_mode` config option allows
forcing one parser.

**Important:** `^` is ambiguous between Wolfram (power) and Python (XOR).
`parse_mathematica("x^2")` correctly produces `x**2`, while
`parse_expr("x^2")` produces `Xor(x, 2)`. The Mathematica-first strategy
handles this correctly. When `parse_mode="python"` is set, users MUST use
`**` for exponentiation.

If both parsers fail, the adapter returns `EXECUTION_ERROR` with the parse
error message in `metadata["error"]`.

**Trust boundary:** Expression strings come from TOML test files, which are
trusted input. `parse_expr()` uses `eval()` internally — this is acceptable
for trusted input but the adapter SHOULD restrict `local_dict` to known
mathematical symbols when feasible.

### Result format

The adapter produces `ValidationToken` results with:
- `result["repr"]`: `str(expr)` — human-readable SymPy string form
- `result["type"]`: `type(expr).__name__` — SymPy type (e.g., `"Add"`, `"Integral"`, `"Pow"`)
- `result["properties"]`: `{}` — empty dict for forward compatibility (matches `OracleAdapter._map_result()` at `src/elegua/wolfram/adapter.py:163`)
- `result["numeric_samples"]`: list of `{"vars": {...}, "value": float}` (only when sample_points provided)

### Unevaluated results

SymPy may return an unevaluated `Integral(f, x)` when it cannot solve an
integral. This is distinct from an error — the call succeeds but the result
is not a closed-form antiderivative. The adapter detects this by checking
`result_expr.has(sympy.Integral)` and sets `metadata["unevaluated"] = True`.
The status remains `OK` (SymPy did not error), but downstream comparison
will correctly fail at L1/L2 since the repr contains `Integral(...)`.

### Numeric samples via lambdify

**Data flow:** Currently, the bridge loader's `Expected` dataclass
(`src/elegua/bridge.py:44-53`) does NOT have a `sample_points` field, and
`IsolatedRunner` does not inject `Expected` fields into task payloads.

Rather than modifying the bridge (which is a cross-cutting change), the
`SympyAdapter` accepts `sample_points` via its constructor:

```python
adapter = SympyAdapter(
    timeout=30.0,
    sample_points=[{"x": 0.5}, {"x": 1.0}, {"x": 2.0}],
)
```

These points are applied to ALL tasks executed by this adapter instance.
This is appropriate because sample points are a verification strategy
concern (how to compare), not a per-test concern (what to test).

Future work: extend `Expected` with optional `sample_points` and wire
through `IsolatedRunner` for per-test sample specification. This would
be a separate openspec change affecting `orchestrator-core`.

When sample points are configured, the adapter evaluates the result
expression at those points using `sympy.lambdify`:

```python
if self._sample_points:
    fn = sympy.lambdify(variables, result_expr, modules="numpy")
    samples = []
    for point in self._sample_points:
        try:
            val = complex(fn(**point))
            if isinstance(val, complex) and val.imag != 0:
                continue  # skip complex results
            fval = float(val.real)
            if not math.isfinite(fval):
                continue  # skip nan/inf
            samples.append({"vars": point, "value": fval})
        except Exception:
            pass  # skip any domain error (TypeError, ZeroDivision, etc.)
    token.result["numeric_samples"] = samples
```

If no sample points are configured, the adapter does NOT generate samples
or add a `numeric_samples` key to the result.

### Timeout handling

SymPy's `integrate()` can hang indefinitely on hard integrands. The adapter
uses `concurrent.futures.ThreadPoolExecutor` with a configurable timeout
(default: 30s), matching the pattern in `src/elegua/wolfram/kernel.py`.

On timeout, the adapter returns `TaskStatus.TIMEOUT` — the test does not
crash; it gets classified as a timeout and the pipeline continues.

**Limitation:** `ThreadPoolExecutor` timeout cannot kill a stuck C extension
(e.g., FLINT via SymPy). Acceptable for MVP; process-based isolation is
future work.

### Package structure

```
src/elegua/sympy/
├── __init__.py      # Public exports: SympyAdapter
├── adapter.py       # SympyAdapter implementation
└── parsing.py       # Expression parsing helpers (parse_mathematica → parse_expr fallback)
```

Follows the same pattern as `src/elegua/wolfram/`.

## Usage

End-to-end example using SympyAdapter with existing RUBI TOML test files:

```python
from elegua.bridge import load_test_file
from elegua.isolation import IsolatedRunner
from elegua.sympy import SympyAdapter
from elegua.verdict import evaluate_expected

# Load a RUBI test file (Wolfram notation — parsed automatically)
tf = load_test_file("tests/fixtures/rubi_exp.toml")

# Run through SymPy — no Docker, no license, no setup
adapter = SympyAdapter(timeout=30.0)
runner = IsolatedRunner(adapter)
with runner:
    results = runner.run(tf)

# Check verdicts
for result, tc in zip(results, tf.tests, strict=True):
    verdict = evaluate_expected(result, tc)
    print(f"{tc.id}: {verdict.status}")
```

With L4 numeric comparison (sample points on adapter):

```python
from elegua.compare_numeric import make_numeric_comparator
from elegua.comparison import ComparisonPipeline
from elegua.sympy import SympyAdapter
from elegua.wolfram import OracleAdapter
from elegua.multitier import MultiTierRunner

points = [{"x": 0.5}, {"x": 1.0}, {"x": 2.0}, {"x": 3.0}]

oracle = OracleAdapter(base_url="http://localhost:8765")
iut = SympyAdapter(timeout=30.0, sample_points=points)

pipeline = ComparisonPipeline()
pipeline.register(4, "numeric", make_numeric_comparator(tol=1e-6, min_samples=2))

runner = MultiTierRunner(oracle=oracle, iut=iut, pipeline=pipeline)
# L4 resolves equivalent-but-different forms via numeric sampling
```

## Risks / Trade-offs

- **SymPy can return wrong results silently** — this is a known issue
  (documented in GitHub issues #21721, #23613, #28186). Mitigated by: using
  SymPy as IUT not oracle, and L4 numeric comparison catches many errors.
- **SymPy is slow for large expressions** — timeout handling prevents hangs,
  but some integrals will timeout rather than producing results. Acceptable
  for verification (timeout = inconclusive, not wrong).
- **`parse_mathematica()` has gaps** — not all Wolfram syntax converts cleanly.
  The fallback chain returns `EXECUTION_ERROR` with the parse error in metadata.
- **Thread-based timeout** — cannot kill stuck C extensions. Acceptable for
  MVP; process-based isolation is future work.

## Open Questions

None — all previously open questions resolved in this revision.
