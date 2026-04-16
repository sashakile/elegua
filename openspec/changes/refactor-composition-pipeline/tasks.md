## 1. Layer key exclusion refactor (proposal item 2)

- [ ] 1.1 Add `exclude_keys: frozenset[str]` field to `_RegisteredLayer` dataclass in `comparison.py`
- [ ] 1.2 Update `ComparisonPipeline.register()` to accept optional `exclude_keys` parameter
- [ ] 1.3 Update `ComparisonPipeline.compare()` to collect higher-layer exclusions and strip before dispatch
- [ ] 1.4 Remove hardcoded `_L4_KEYS` constant and `_strip_l4()` function from `comparison.py`
- [ ] 1.5 Remove `_L4_KEYS` references from `_canonicalize()` (pipeline-level stripping makes them unnecessary)
- [ ] 1.6 Update default L4 registration in tests/docs to pass `exclude_keys=frozenset({"numeric_samples"})`
- [ ] 1.7 Write tests: layer exclusion is applied correctly; backward compat with no `exclude_keys`; multi-layer exclusion union
- [ ] 1.8 Update orchestrator-core spec §4 (4-Layer Comparison Pipeline) to reflect declarative exclusion

## 2. Verdict–ComparisonResult bridge (proposal item 1)

- [ ] 2.1 Add `Verdict.from_comparison(result: ComparisonResult)` classmethod to `verdict.py` with default branch for unknown statuses
- [ ] 2.2 Write tests: mapping for OK, MATH_MISMATCH, EXECUTION_ERROR, TIMEOUT, and unknown status fallback
- [ ] 2.3 Update testing-architecture spec §4 (Verdict Evaluation) to document the bridge method

## 3. Injectable result mapper for OracleAdapter (proposal item 3)

- [ ] 3.1 Add `result_mapper` parameter to `OracleAdapter.__init__()` in `wolfram/adapter.py`
- [ ] 3.2 Update `execute()` to delegate to `result_mapper` when provided, else `_map_result()`
- [ ] 3.3 Write tests: custom result mapper is called; default behavior preserved when `None`
- [ ] 3.4 Update orchestrator-core spec §8 (Extension Architecture) to document injectable mapper

## 4. Deprecate runner.py (proposal item 4)

- [ ] 4.1 Add `DeprecationWarning` to `load_toml_tasks()` and `run_tasks()` in `runner.py`
- [ ] 4.2 Update existing tests to assert deprecation with `pytest.warns(DeprecationWarning)`
- [ ] 4.3 Update orchestrator-core spec §3 (Task Lifecycle) to note deprecation
