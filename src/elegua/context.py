"""Execution context — variable store for store_as chaining.

Provides a per-suite binding store that supports $name substitution
in task payload strings and snapshot/restore for scope management
(setup bindings are file-wide, test bindings are per-test).
"""

from __future__ import annotations

import re
from typing import Any

_REF_RE = re.compile(r"\$(\w+)")


class ExecutionContext:
    """Mutable name-to-value store with $name substitution and scoping."""

    def __init__(self) -> None:
        self._bindings: dict[str, str] = {}

    def store(self, name: str, value: str) -> None:
        """Bind *name* to *value*."""
        self._bindings[name] = value

    def resolve(self, name: str) -> str | None:
        """Look up a binding. Returns None if not found."""
        return self._bindings.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._bindings

    def snapshot(self) -> dict[str, str]:
        """Return an independent copy of current bindings."""
        return dict(self._bindings)

    def restore(self, bindings: dict[str, str]) -> None:
        """Replace current bindings with a previously captured snapshot."""
        self._bindings = dict(bindings)

    def resolve_refs(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of *payload* with ``$name`` references substituted.

        Only top-level string values are substituted. Unknown references
        are left as-is.
        """
        return {
            key: self._sub_refs(val) if isinstance(val, str) else val
            for key, val in payload.items()
        }

    def _sub_refs(self, text: str) -> str:
        return _REF_RE.sub(lambda m: self._bindings.get(m.group(1), m.group(0)), text)
