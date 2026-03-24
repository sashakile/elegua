## 1. Expression parsing (TDD)

- [ ] 1.1 Write tests for expression parsing: Wolfram syntax, Python syntax, `^` ambiguity, fallback chain, explicit parse_mode, unparsable input
- [ ] 1.2 Create `src/elegua/sympy/parsing.py` — implement parse chain (Mathematica → Python fallback)
- [ ] 1.3 Verify parsing tests pass

## 2. Core adapter (TDD)

- [ ] 2.1 Add `sympy>=1.13` to `[project.optional-dependencies] sympy` in pyproject.toml
- [ ] 2.2 Write tests for action dispatch: Integrate, Differentiate, Simplify, Solve, Series, Limit, unknown action, missing required fields, SymPy computation error
- [ ] 2.3 Write test for unevaluated integral detection (`metadata["unevaluated"]`)
- [ ] 2.4 Write test for timeout handling (mock slow computation, verify returns within timeout + 2s)
- [ ] 2.5 Create `src/elegua/sympy/adapter.py` — `SympyAdapter(Adapter)` with action registry, timeout, unevaluated detection, computation error handling
- [ ] 2.6 Create `src/elegua/sympy/__init__.py` with public exports
- [ ] 2.7 Verify action dispatch and timeout tests pass

## 3. Numeric samples / L4 (TDD)

- [ ] 3.1 Write tests for lambdify-based sample generation: happy path with constructor sample_points, domain errors (poles, nan, inf, complex), no sample_points configured
- [ ] 3.2 Implement lambdify-based numeric sample generation in adapter (reads from self._sample_points)
- [ ] 3.3 Write integration test: L4 comparison catches equivalent-but-different forms (e.g., `log(a) + log(b)` vs `log(a*b)` resolved as OK via matching numeric samples)
- [ ] 3.4 Verify L4 tests pass

## 4. End-to-end integration (TDD)

- [ ] 4.1 Write integration test: run existing RUBI TOML fixtures (`rubi_exp.toml`, `rubi_trig.toml`, `rubi_power.toml`) through SympyAdapter
- [ ] 4.2 Verify RUBI integration tests pass

## 5. Quality checks

- [ ] 5.1 Verify pyright passes on all new code in `src/elegua/sympy/`
- [ ] 5.2 Verify ruff passes on all new code
- [ ] 5.3 Docstrings on public API (SympyAdapter, parse modes, action registry)
- [ ] 5.4 Usage example in SympyAdapter class docstring showing RUBI workflow
