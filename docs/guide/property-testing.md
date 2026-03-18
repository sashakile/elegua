# Property-based testing

## Overview

The property runner validates mathematical laws by generating random inputs with reproducible PCG64 seeds and checking that properties hold across all samples.

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

- `generators` — list of variable generators with `name` and `type`
- `setup` — list of setup actions to run before testing

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

## Generator registry

Register domain-specific generators that produce random values from a seeded RNG:

```python
from elegua.property import GeneratorRegistry

registry = GeneratorRegistry()
registry.register("integer", lambda rng: int(rng.integers(-1000, 1000)))
registry.register("float", lambda rng: float(rng.uniform(-1.0, 1.0)))
registry.register("tensor_rank", lambda rng: int(rng.integers(0, 5)))
```

The `rng` parameter is a `numpy.random.Generator` backed by PCG64.

## Running properties

```python
from elegua.property import PropertyRunner

runner = PropertyRunner(registry=registry)
result = runner.run(spec, evaluator=my_evaluator, seed=42, samples=100)

print(result.passed)       # True/False
print(result.samples_run)  # 100
print(result.failures)     # list of Failure(sample_index, bindings)
```

## Evaluator functions

An evaluator takes the law string and a dict of variable bindings, and returns `True` if the property holds:

```python
def my_evaluator(law: str, bindings: dict) -> bool:
    x = bindings["$x"]
    # Check: f(f(x)) == x where f is negation
    return -(-x) == x
```

## Reproducibility

The same seed always produces the same sample sequence across platforms, thanks to PCG64:

```python
samples_a = runner.generate_samples(spec, seed=42, count=10)
samples_b = runner.generate_samples(spec, seed=42, count=10)
assert samples_a == samples_b  # always true
```

## Failure reporting

When a property fails, each `Failure` records:

- `sample_index` — which sample number failed
- `bindings` — the variable values that caused the failure

```python
if not result.passed:
    for failure in result.failures:
        print(f"Sample {failure.sample_index}: {failure.bindings}")
```
