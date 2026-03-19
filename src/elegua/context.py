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
        are left as-is (with a RuntimeWarning emitted).
        """
        resolved = {}
        for key, val in payload.items():
            if isinstance(val, str):
                new_val, unresolved = self._sub_refs(val)
                for name in unresolved:
                    import warnings

                    warnings.warn(f"Unresolved reference ${name}", RuntimeWarning, stacklevel=2)
                resolved[key] = new_val
            else:
                resolved[key] = val
        return resolved

    def _sub_refs(self, text: str) -> tuple[str, list[str]]:
        unresolved: list[str] = []

        def _replace(m: re.Match[str]) -> str:
            name = m.group(1)
            value = self._bindings.get(name)
            if value is None:
                unresolved.append(name)
                return m.group(0)
            return value

        result = _REF_RE.sub(_replace, text)
        return result, unresolved
