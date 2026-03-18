"""4-Layer Comparison Pipeline for ValidationToken results.

Layer 1 (Identity): Structural equality of result dicts.
Layer 2 (Structural): AST isomorphism — sorted canonical form comparison.
Layer 3 (Canonical): Pluggable normalizer rules (domain-specific, not yet implemented).
Layer 4 (Invariant): Numerical/PBT validation (domain-specific, not yet implemented).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from elegua.models import ValidationToken
from elegua.task import TaskStatus


@dataclass(frozen=True)
class ComparisonResult:
    """Result of running the comparison pipeline."""

    status: TaskStatus
    layer: int


def compare_identity(token_a: ValidationToken, token_b: ValidationToken) -> TaskStatus:
    """Layer 1: Return OK if token results are structurally equal."""
    if token_a.result == token_b.result:
        return TaskStatus.OK
    return TaskStatus.MATH_MISMATCH


def _canonicalize(value: Any) -> Any:
    """Recursively sort dicts and lists-of-sortable for structural comparison."""
    if isinstance(value, dict):
        return {k: _canonicalize(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        canonical = [_canonicalize(v) for v in value]
        return sorted(canonical, key=repr)
    return value


def compare_structural(token_a: ValidationToken, token_b: ValidationToken) -> TaskStatus:
    """Layer 2: AST isomorphism via sorted canonical form."""
    if _canonicalize(token_a.result) == _canonicalize(token_b.result):
        return TaskStatus.OK
    return TaskStatus.MATH_MISMATCH


def compare_pipeline(token_a: ValidationToken, token_b: ValidationToken) -> ComparisonResult:
    """Run the comparison pipeline, stopping at the first layer that matches.

    Currently implements Layer 1 (Identity) and Layer 2 (Structural).
    Layers 3-4 are domain-specific extension points.
    """
    # Layer 1: Identity
    if compare_identity(token_a, token_b) == TaskStatus.OK:
        return ComparisonResult(status=TaskStatus.OK, layer=1)

    # Layer 2: Structural
    if compare_structural(token_a, token_b) == TaskStatus.OK:
        return ComparisonResult(status=TaskStatus.OK, layer=2)

    # No higher layers registered — report mismatch at last layer checked
    return ComparisonResult(status=TaskStatus.MATH_MISMATCH, layer=2)
