"""4-Layer Comparison Pipeline for ValidationToken results.

Layer 1 (Identity): Structural equality of result dicts.
Layer 2 (Structural): AST isomorphism — sorted canonical form comparison.
Layer 3 (Canonical): pluggable — register via ComparisonPipeline.register().
Layer 4 (Invariant): pluggable — register via ComparisonPipeline.register().
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from elegua.errors import SchemaError
from elegua.models import ValidationToken
from elegua.task import TaskStatus

LayerFn = Callable[[ValidationToken, ValidationToken], TaskStatus]


@dataclass(frozen=True)
class ComparisonResult:
    """Result of running the comparison pipeline."""

    status: TaskStatus
    layer: int
    layer_name: str = ""


# Keys that carry L4 (numeric/invariant) data and must be excluded from
# L1 identity and L2 structural comparison.
_L4_KEYS = frozenset({"numeric_samples"})


def _strip_l4(result: dict[str, Any] | None) -> dict[str, Any] | None:
    """Remove L4-only keys from a result dict before L1/L2 comparison."""
    if result is None or not _L4_KEYS.intersection(result):
        return result
    return {k: v for k, v in result.items() if k not in _L4_KEYS}


def compare_identity(token_a: ValidationToken, token_b: ValidationToken) -> TaskStatus:
    """Layer 1: Return OK if token results are structurally equal."""
    if _strip_l4(token_a.result) == _strip_l4(token_b.result):
        return TaskStatus.OK
    return TaskStatus.MATH_MISMATCH


def _canonicalize(value: Any) -> Any:
    """Recursively sort dicts and lists-of-sortable for structural comparison."""
    if isinstance(value, dict):
        return {k: _canonicalize(v) for k, v in sorted(value.items()) if k not in _L4_KEYS}
    if isinstance(value, list):
        canonical = [_canonicalize(v) for v in value]
        return sorted(canonical, key=repr)
    return value


def compare_structural(token_a: ValidationToken, token_b: ValidationToken) -> TaskStatus:
    """Layer 2: AST isomorphism via sorted canonical form."""
    if _canonicalize(token_a.result) == _canonicalize(token_b.result):
        return TaskStatus.OK
    return TaskStatus.MATH_MISMATCH


@dataclass
class _RegisteredLayer:
    num: int
    name: str
    fn: LayerFn


class ComparisonPipeline:
    """Multi-layer comparison pipeline with pluggable layer registration.

    By default registers L1 (identity) and L2 (structural). Domain-specific
    layers (L3 canonical, L4 numeric, etc.) are added via ``register()``.
    """

    def __init__(self, *, default_layers: bool = True) -> None:
        self._layers: list[_RegisteredLayer] = []
        if default_layers:
            self.register(1, "identity", compare_identity)
            self.register(2, "structural", compare_structural)

    @property
    def layers(self) -> list[tuple[int, str]]:
        """Return registered layers as (num, name) pairs, sorted by num."""
        return [(layer.num, layer.name) for layer in self._layers]

    def register(self, layer_num: int, name: str, fn: LayerFn) -> None:
        """Register a comparison layer. Layers run in ``layer_num`` order."""
        existing = {layer.num for layer in self._layers}
        if layer_num in existing:
            raise SchemaError(f"Duplicate layer number {layer_num}: already registered")
        self._layers.append(_RegisteredLayer(num=layer_num, name=name, fn=fn))
        self._layers.sort(key=lambda entry: entry.num)

    def compare(self, token_a: ValidationToken, token_b: ValidationToken) -> ComparisonResult:
        """Run layers in order, stopping at the first match."""
        if not self._layers:
            raise SchemaError("ComparisonPipeline has no registered layers")
        last_layer = 0
        last_name = ""
        for layer in self._layers:
            last_layer = layer.num
            last_name = layer.name
            try:
                result = layer.fn(token_a, token_b)
            except Exception as exc:
                raise RuntimeError(f"Layer {layer.num} ({layer.name!r}) raised: {exc}") from exc
            if result == TaskStatus.OK:
                return ComparisonResult(
                    status=TaskStatus.OK, layer=layer.num, layer_name=layer.name
                )
        return ComparisonResult(
            status=TaskStatus.MATH_MISMATCH, layer=last_layer, layer_name=last_name
        )


def compare_pipeline(token_a: ValidationToken, token_b: ValidationToken) -> ComparisonResult:
    """Run the default comparison pipeline (L1 identity + L2 structural)."""
    return ComparisonPipeline().compare(token_a, token_b)
