## 1. Dependencies and Foundation
- [x] 1.1 Add `hypothesis>=6.0` to core dependencies in `pyproject.toml`
- [x] 1.2 Remove `numpy` import from `property.py` (numpy stays for `compare_numeric.py`)

## 2. Strategy Registry (replaces GeneratorRegistry)
- [x] 2.1 Implement `StrategyRegistry` mapping type names → `SearchStrategy` instances
- [x] 2.2 Support callable factories: `register("name", lambda params: st.integers(**params))`
- [x] 2.3 Support pre-built strategies: `register("name", st.integers(-100, 100))`
- [x] 2.4 Keep `GeneratorRegistry` as deprecated alias wrapping callables in `st.builds`
- [x] 2.5 Write tests for strategy registration, lookup, and params passthrough

## 3. PropertySpec TOML Extension
- [x] 3.1 Add optional `params` dict to `GeneratorSpec` model
- [x] 3.2 Add optional `[settings]` table to `PropertySpec` (max_examples, deadline)
- [x] 3.3 Validate that existing TOML fixtures parse unchanged (backward compat)
- [x] 3.4 Write test for TOML with `params` and `settings`

## 4. HypothesisPropertyRunner (replaces PropertyRunner)
- [x] 4.1 Implement `run()` that builds a `@given`-decorated function from spec + registry
- [x] 4.2 Convert Hypothesis `AssertionError` exceptions into `PropertyResult` with shrunk `Failure`
- [x] 4.3 Support `settings` from spec (max_examples, deadline)
- [x] 4.4 Handle zero-generator specs (law-only, no random inputs)
- [x] 4.5 Propagate evaluator exceptions with context (law, bindings)
- [x] 4.6 Write tests: passing property, failing with shrunk counterexample, settings override

## 5. Result Types
- [x] 5.1 Extend `Failure` with `shrunk_bindings: dict[str, Any]` field
- [x] 5.2 Ensure `PropertyResult` is backward-compatible (passed, samples_run, failures)
- [x] 5.3 Write tests for result shape

## 6. Public API and Exports
- [x] 6.1 Update `__init__.py` exports: add `StrategyRegistry`, keep `GeneratorRegistry` as alias
- [x] 6.2 Update `__all__` list
- [x] 6.3 Add deprecation warning to `GeneratorRegistry` constructor

## 7. Test Migration
- [x] 7.1 Update `test_property.py` to use `StrategyRegistry` and new runner
- [x] 7.2 Verify shrinking produces minimal counterexamples in failure tests
- [x] 7.3 Verify example database persists across runs
- [x] 7.4 Verify existing `involution.toml` fixture works unchanged

## 8. Spec and Docs
- [x] 8.1 Update `property-testing` spec via delta
- [x] 8.2 Update `docs/guide/property-testing.md`
