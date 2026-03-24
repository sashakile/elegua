# Change: Add SymPy adapter as optional extra

**Change-ID:** `add-sympy-adapter`

## Why

Elegua claims domain agnosticism but currently only ships one backend
(`elegua[wolfram]`). Adding a SymPy adapter proves the adapter protocol
works for a non-HTTP, in-process Python CAS. It also provides an
in-process backend requiring only a pip install — no Docker, no kernel,
no license — making elegua usable in CI environments and by open-source
contributors without Wolfram access.

## What Changes

- New optional extra: `pip install elegua[sympy]`
- New subpackage: `src/elegua/sympy/` containing `SympyAdapter`
- `SympyAdapter` maps `EleguaTask` actions to SymPy function calls
  (`integrate`, `diff`, `simplify`, `solve`, `series`, `limit`)
- Adapter generates `numeric_samples` via `sympy.lambdify` for L4 comparison
- Wolfram-syntax expression parsing (`parse_mathematica()`) with Python
  fallback, enabling reuse of existing Wolfram-notation TOML test files

## Impact

- Affected specs: `orchestrator-core` (new adapter implementation)
- Affected code: `src/elegua/sympy/`, `pyproject.toml`, `tests/test_sympy_adapter.py`
- No breaking changes — purely additive
