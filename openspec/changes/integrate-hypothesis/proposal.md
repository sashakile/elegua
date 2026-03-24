# Change: Integrate Hypothesis for Full Property-Based Testing

## Why

The current `PropertyRunner` is a minimal sample-check loop: generate N random inputs, evaluate a law, collect failures. It lacks the features that make PBT effective for catching subtle mathematical bugs:

- **No shrinking** — failures report the original random input, not a minimal counterexample. A tensor with 50 components doesn't tell you which component matters.
- **No composable strategies** — `GeneratorRegistry` is a flat name→function map. You can't compose, filter, map, or combine generators. Building "symmetric rank-2 tensor on a 4-manifold" requires manual wiring.
- **No example database** — past failures are forgotten between runs. A regression that took 10 minutes of fuzzing to find must be rediscovered from scratch.
- **No stateful testing** — can't test sequences of operations (e.g., "define tensor, then contract, then symmetrize" as a random walk).
- **No health checks** — no detection of flaky tests, degenerate data generation, or excessive filtering.

Hypothesis provides all of these as battle-tested, maintained infrastructure.

### Separation of Concerns

The current code conflates two distinct uses of randomness:

1. **PBT (Layer 2)**: Check mathematical laws hold for random inputs. Shrinking and strategies matter. Cross-platform determinism does not — this runs in Python only.
2. **L4 numeric sampling**: Generate deterministic sample points that both Python and Julia evaluate at. Cross-platform PCG64 reproducibility matters. Shrinking does not.

This change separates them: Hypothesis owns PBT, PCG64 stays for L4 numeric comparison.

## What Changes

- **BREAKING**: Replace `PropertyRunner` with `HypothesisPropertyRunner` backed by `hypothesis.given` / `hypothesis.strategies`
- **BREAKING**: Replace `GeneratorRegistry` with `StrategyRegistry` mapping TOML type names → Hypothesis strategies
- **Keep**: `PropertySpec` TOML format (extended with optional strategy parameters)
- **Keep**: `PropertyResult`, `Failure` result types (enriched with shrunk counterexamples)
- **Keep**: `PropertyValidationError` error type
- **Keep**: PCG64 sampling in `compare_numeric.py` (completely untouched)
- **Add**: `hypothesis` as a core dependency
- **Remove**: `numpy` dependency from property module (numpy stays for `compare_numeric.py`)

## Impact

- Affected specs: `property-testing`
- Affected code: `src/elegua/property.py`, `tests/test_property.py`, `pyproject.toml`
- Public API: `GeneratorRegistry` renamed to `StrategyRegistry`, `PropertyRunner` API changes (no more `seed`/`samples` params — Hypothesis settings control these)
- Backward compatibility: `GeneratorRegistry` kept as deprecated alias for one release
