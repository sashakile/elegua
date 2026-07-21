# Capabilities

**Adapters declare what they can do; fixtures declare what they need. The runner checks that requirements are met before executing any test.**

> **What it does** — The capability system lets you declare what an adapter supports (``gradient``, ``deterministic``, etc.) and what a fixture requires. The runner skips fixtures whose requirements are not met, with a structured reason.  
> **Use this when** — You're writing a fixture that depends on adapter features, or building an adapter that provides them.  
> **Prerequisites** — [Writing an adapter](adapters.md) and [TOML format](toml-format.md).  
> **Outcome** — Know the standard capability vocabulary, how to declare capabilities in adapters and fixtures, and how tier overrides work.

## Standard capability vocabulary

The following capability names are predefined. All are optional — only declare what your adapter actually supports.

| Capability | Meaning |
|------------|---------|
| `gradient` | Adapter can compute gradients, sensitivities, or derivatives |
| `deterministic` | Adapter produces identical results for identical inputs |
| `seedable` | Adapter accepts an explicit random seed |
| `symbolic` | Adapter works with symbolic (CAS) expressions |
| `numerical` | Adapter works with numerical (floating-point) expressions |

### Namespace guidance

The capability vocabulary is **open** — plugins and custom adapters can define their own capability names. Follow these conventions:

- **Prefer existing names** — use the standard vocabulary above before inventing new ones
- **Prefix plugin-owned names** — use a namespace prefix to avoid collisions, for example ``finance_greeks``, ``tensor_contraction``
- **Document custom capabilities** — if you add a new capability, document it in your adapter's docstring or plugin README

## Declaring capabilities in an adapter

Override the ``capabilities`` property on your ``Adapter`` subclass:

```python
from elegua.adapter import Adapter
from elegua.models import ValidationToken
from elegua.task import EleguaTask, TaskStatus

class MyAdapter(Adapter):
    @property
    def adapter_id(self) -> str:
        return "my-engine"

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset({"gradient", "deterministic", "seedable"})

    def execute(self, task: EleguaTask) -> ValidationToken:
        ...
```

The default ``capabilities`` property returns an empty frozenset — adapters that do not override it declare no capabilities.

### Shipped adapter capabilities

| Adapter | Advertised capabilities | Notes |
|---------|------------------------|-------|
| ``WolframAdapter`` | (none) | Built-in stub for architecture testing |
| ``OracleAdapter`` | (none) | Generic HTTP adapter — override to declare your engine's capabilities |
| ``SympyAdapter`` | (none) | SymPy-based adapter — override to declare capabilities |

All shipped adapters default to no declared capabilities. If your use of an adapter requires capabilities (for example, a ``gradient`` fixture run against a Wolfram kernel), create a subclass:

```python
class MyWolframAdapter(OracleAdapter):
    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset({"gradient", "symbolic", "deterministic"})
```

## Declaring requirements in a fixture

In the ``[meta]`` section of a TOML fixture, use ``requires`` and ``prefers`` to declare what the fixture needs from an adapter:

```toml
[meta]
id          = "gradient-check"
description = "Verify gradient computation"
requires    = ["gradient", "deterministic"]
prefers     = ["symbolic"]
```

- ``requires`` — mandatory capabilities. If the adapter does not provide all of them, the fixture is skipped with a structured reason.
- ``prefers`` — optional capabilities. The fixture runs even if the adapter lacks them; preferences are available for the runner to use when scheduling.

### Tier-specific overrides

Use ``tier_overrides`` to exempt specific capabilities at certain tiers:

```toml
[meta]
id          = "noisy-gradient"
description = "Gradient check with stochastic tolerance"
requires    = ["gradient", "deterministic"]

[meta.tier_overrides.iut]
exempts = ["deterministic"]
```

This tells the runner: the oracle tier must be deterministic, but the IUT tier is exempt from that requirement.

## How the runner uses capabilities

When ``IsolatedRunner.run()`` is called:

1. The runner reads the fixture's ``requires`` and ``tier_overrides``
2. It calls ``check_capabilities(adapter.capabilities, requires, exempts)``
3. If any capabilities are missing, all tests in the fixture are returned as skipped with a reason like ``adapter 'my-engine' missing capabilities: gradient``
4. If all requirements are met, the fixture runs normally

The ``check_capabilities`` function is also available for direct use:

```python
from elegua.capabilities import check_capabilities

ok, missing = check_capabilities(
    adapter_capabilities=frozenset({"gradient", "deterministic"}),
    requires=frozenset({"gradient", "symbolic"}),
)
print(ok)       # False
print(missing)  # frozenset({"symbolic"})
```

## Capability negotiation across tiers

In multi-tier workflows (``MultiTierRunner``), each tier role (``oracle``, ``iut``) can have its own capability exemptions. The same fixture runs against both tiers, but the IUT tier can be allowed to skip capabilities that the oracle tier must support:

```toml
[meta]
id          = "cross-tier-gradient"
description = "Gradient check with relaxed IUT requirements"
requires    = ["gradient", "deterministic", "seedable"]

[meta.tier_overrides.iut]
exempts = ["deterministic", "seedable"]
```

This is useful when the oracle is a high-fidelity reference implementation and the IUT is still under development.