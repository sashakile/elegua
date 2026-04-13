# Property-based testing

Property-based testing is Layer 2 of the [testing architecture](../architecture.md). It validates mathematical laws by generating random inputs via [Hypothesis](https://hypothesis.readthedocs.io/) and checking that properties hold, with automatic shrinking of counterexamples.

## Property spec format

Properties are defined in TOML:

```toml
name = "negate_involution"
layer = "property"
law = "f(f($x)) == $x"

[[generators]]
name = "$x"
type = "integer"

[[setup]]
action = "negate"
```

Required fields:

- `name` — identifier for the property
- `layer` — must be `"property"`
- `law` — the property to validate, with `$`-prefixed variable placeholders

Optional fields:

- `generators` — list of variable generators with `name`, `type`, and optional `params`
- `setup` — list of setup actions to run before testing
- `settings` — Hypothesis configuration (see below)

### Generator parameters

Generators can include a `params` table to configure the strategy:

```toml
[[generators]]
name = "$x"
type = "bounded_int"
[generators.params]
min_value = 0
max_value = 100
```

### Settings

```toml
[settings]
max_examples = 200   # default: 100
deadline = 5000      # ms, default: 1000
```

## Loading a property spec

```python
from pathlib import Path
from elegua.property import PropertySpec

spec = PropertySpec.from_toml(Path("tests/fixtures/involution.toml"))
print(spec.name)        # "negate_involution"
print(spec.law)         # "f(f($x)) == $x"
print(spec.generators)  # [GeneratorSpec(name='$x', type='integer')]
```

Invalid specs raise `PropertyValidationError`.

## Strategy registry

Register Hypothesis strategies that map TOML type names to data generators:

```python
from hypothesis import strategies as st
from elegua.property import StrategyRegistry

registry = StrategyRegistry()
registry.register("integer", st.integers(-1000, 1000))
registry.register("positive_real", st.floats(min_value=0.01, max_value=1e6))
```

### Callable factories

Register a callable that accepts params from the TOML spec:

```python
registry.register(
    "bounded_int",
    lambda min_value=0, max_value=100: st.integers(min_value, max_value),
)
```

### Composing strategies

Because entries are Hypothesis strategies, you can compose them freely:

```python
registry.register(
    "rank2_tensor",
    st.builds(make_rank2_tensor, dim=st.integers(2, 6)),
)
registry.register(
    "metric_or_connection",
    st.one_of(st.builds(make_metric), st.builds(make_connection)),
)
```

## Running properties

```python
from elegua.property import PropertyRunner

runner = PropertyRunner(registry=registry)
result = runner.run(spec, evaluator=my_evaluator)

print(result.passed)       # True/False
print(result.samples_run)  # number of examples tested
print(result.failures)     # list of Failure with shrunk counterexamples
```

Override settings per call:

```python
result = runner.run(spec, evaluator=my_evaluator, max_examples=500, deadline=None)
```

## Evaluator functions

An evaluator takes the law string and a dict of variable bindings, and returns `True` if the property holds:

```python
# Local evaluator — for properties computable in Python
def my_evaluator(law: str, bindings: dict) -> bool:
    x = bindings["$x"]
    return -(-x) == x

# Adapter-backed evaluator — for properties requiring a symbolic engine
def adapter_evaluator(law: str, bindings: dict) -> bool:
    token = my_adapter.execute(EleguaTask(action="Evaluate", payload=bindings))
    return token.status == TaskStatus.OK
```

## Shrinking

When a property fails, Hypothesis automatically reduces the failing input to a minimal counterexample:

```python
result = runner.run(spec, evaluator=lambda law, b: b["$x"] >= 0)
if not result.passed:
    failure = result.failures[0]
    print(failure.shrunk_bindings)  # {"$x": -1} — minimal counterexample
```

## Failure reporting

Each `Failure` records:

- `sample_index` — which sample number failed
- `bindings` — the variable values at the point of failure
- `shrunk_bindings` — the minimal counterexample after shrinking

```python
if not result.passed:
    for failure in result.failures:
        print(f"Shrunk to: {failure.shrunk_bindings}")
```

## Migration from GeneratorRegistry

`GeneratorRegistry` is deprecated. Replace:

```python
# Old
registry = GeneratorRegistry()
registry.register("integer", lambda rng: int(rng.integers(-1000, 1000)))

# New
registry = StrategyRegistry()
registry.register("integer", st.integers(-1000, 1000))
```

`GeneratorRegistry` still works but emits a `DeprecationWarning`.

## Note on L4 numeric comparison

PCG64 cross-platform deterministic sampling is used for L4 numeric comparison (`compare_numeric.py`), not for property-based testing. These are separate concerns — Hypothesis owns PBT randomness, PCG64 owns cross-CAS sample point generation.
