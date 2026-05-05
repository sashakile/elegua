"""Adapter capability negotiation for Eleguá.

Standard capability names (open string vocabulary — plugins may define more):

  gradient        — adapter can compute gradients / sensitivities
  deterministic   — adapter produces identical results for identical inputs
  seedable        — adapter accepts an explicit random seed
  symbolic        — adapter works with symbolic (CAS) expressions
  numerical       — adapter works with numerical (floating-point) expressions
"""

from __future__ import annotations


def check_capabilities(
    adapter_capabilities: frozenset[str],
    requires: frozenset[str],
    exempts: frozenset[str] = frozenset(),
) -> tuple[bool, frozenset[str]]:
    """Check whether an adapter satisfies fixture capability requirements.

    Returns ``(ok, missing)`` where *ok* is True when all non-exempted
    requirements are met and *missing* is the set of unsatisfied capabilities.

    args:
        adapter_capabilities: Capabilities declared by the adapter.
        requires: Capabilities the fixture requires.
        exempts: Capabilities exempted for this tier (from tier_overrides).
    """
    effective = requires - exempts
    missing = effective - adapter_capabilities
    return (len(missing) == 0, missing)
