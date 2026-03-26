"""Tests for ComparisonPipeline — pluggable layer registration."""

from __future__ import annotations

import pytest

from elegua.comparison import (
    ComparisonPipeline,
)
from elegua.errors import SchemaError
from elegua.models import ValidationToken
from elegua.task import TaskStatus


def _token(result: dict | None = None) -> ValidationToken:
    return ValidationToken(adapter_id="test", status=TaskStatus.OK, result=result)


# --- Default pipeline (L1 + L2) ---


def test_default_pipeline_has_two_layers():
    pipeline = ComparisonPipeline()
    assert len(pipeline.layers) == 2


def test_default_pipeline_identity_match():
    pipeline = ComparisonPipeline()
    a = _token({"x": 1})
    b = _token({"x": 1})
    result = pipeline.compare(a, b)
    assert result.status == TaskStatus.OK
    assert result.layer == 1
    assert result.layer_name == "identity"


def test_default_pipeline_structural_match():
    pipeline = ComparisonPipeline()
    a = _token({"fn": "Add", "args": [1, 2]})
    b = _token({"fn": "Add", "args": [2, 1]})
    result = pipeline.compare(a, b)
    assert result.status == TaskStatus.OK
    assert result.layer == 2
    assert result.layer_name == "structural"


def test_default_pipeline_mismatch():
    pipeline = ComparisonPipeline()
    a = _token({"x": 1})
    b = _token({"x": 2})
    result = pipeline.compare(a, b)
    assert result.status == TaskStatus.MATH_MISMATCH
    assert result.layer == 2


# --- Custom layer registration ---


def test_register_layer_3():
    pipeline = ComparisonPipeline()

    def always_match(a: ValidationToken, b: ValidationToken) -> TaskStatus:
        return TaskStatus.OK

    pipeline.register(3, "custom", always_match)
    assert len(pipeline.layers) == 3


def test_custom_layer_runs_after_builtin():
    """L3 catches what L1+L2 miss."""
    pipeline = ComparisonPipeline()
    called = []

    def custom_layer(a: ValidationToken, b: ValidationToken) -> TaskStatus:
        called.append(True)
        return TaskStatus.OK

    pipeline.register(3, "custom", custom_layer)

    a = _token({"x": 1})
    b = _token({"x": 2})
    result = pipeline.compare(a, b)
    assert result.status == TaskStatus.OK
    assert result.layer == 3
    assert result.layer_name == "custom"
    assert called


def test_custom_layer_skipped_if_earlier_matches():
    """L3 not called when L1 already matches."""
    pipeline = ComparisonPipeline()
    called = []

    def custom_layer(a: ValidationToken, b: ValidationToken) -> TaskStatus:
        called.append(True)
        return TaskStatus.OK

    pipeline.register(3, "custom", custom_layer)

    a = _token({"x": 1})
    b = _token({"x": 1})
    result = pipeline.compare(a, b)
    assert result.layer == 1
    assert not called


def test_register_layer_4():
    pipeline = ComparisonPipeline()

    def layer_3(a: ValidationToken, b: ValidationToken) -> TaskStatus:
        return TaskStatus.MATH_MISMATCH

    def layer_4(a: ValidationToken, b: ValidationToken) -> TaskStatus:
        return TaskStatus.OK

    pipeline.register(3, "canonical", layer_3)
    pipeline.register(4, "numeric", layer_4)

    a = _token({"x": 1})
    b = _token({"x": 2})
    result = pipeline.compare(a, b)
    assert result.status == TaskStatus.OK
    assert result.layer == 4
    assert result.layer_name == "numeric"


def test_all_layers_mismatch():
    pipeline = ComparisonPipeline()

    def never_match(a: ValidationToken, b: ValidationToken) -> TaskStatus:
        return TaskStatus.MATH_MISMATCH

    pipeline.register(3, "canonical", never_match)
    pipeline.register(4, "numeric", never_match)

    a = _token({"x": 1})
    b = _token({"x": 2})
    result = pipeline.compare(a, b)
    assert result.status == TaskStatus.MATH_MISMATCH
    assert result.layer == 4


# --- Empty pipeline ---


def test_empty_pipeline():
    pipeline = ComparisonPipeline(default_layers=False)
    assert len(pipeline.layers) == 0


def test_empty_pipeline_raises_schema_error():
    pipeline = ComparisonPipeline(default_layers=False)
    a = _token({"x": 1})
    b = _token({"x": 1})
    with pytest.raises(SchemaError, match="no registered layers"):
        pipeline.compare(a, b)


# --- Layer ordering ---


def test_layers_run_in_order():
    pipeline = ComparisonPipeline(default_layers=False)
    order = []

    def make_layer(name: str):
        def layer(a: ValidationToken, b: ValidationToken) -> TaskStatus:
            order.append(name)
            return TaskStatus.MATH_MISMATCH

        return layer

    pipeline.register(3, "third", make_layer("third"))
    pipeline.register(1, "first", make_layer("first"))
    pipeline.register(2, "second", make_layer("second"))

    a = _token({"x": 1})
    b = _token({"x": 2})
    pipeline.compare(a, b)
    assert order == ["first", "second", "third"]


# --- Closure over context (domain-specific pattern) ---


def test_layer_with_context_closure():
    """Domain layers can close over context like an oracle client."""
    pipeline = ComparisonPipeline()
    oracle_calls = []

    def make_symbolic_layer(oracle_url: str):
        def compare(a: ValidationToken, b: ValidationToken) -> TaskStatus:
            oracle_calls.append(oracle_url)
            # Simulate: Simplify[lhs - rhs] == 0
            return TaskStatus.OK

        return compare

    pipeline.register(3, "symbolic", make_symbolic_layer("http://localhost:8765"))

    a = _token({"x": 1})
    b = _token({"x": 2})
    result = pipeline.compare(a, b)
    assert result.status == TaskStatus.OK
    assert result.layer == 3
    assert oracle_calls == ["http://localhost:8765"]


# --- L2 ignores numeric_samples (L4 data) ---


def test_exclude_keys_strips_before_lower_layers():
    """Registering L4 with exclude_keys strips those keys from L1/L2 dispatch."""
    pipeline = ComparisonPipeline()

    def numeric_layer(a: ValidationToken, b: ValidationToken) -> TaskStatus:
        return TaskStatus.MATH_MISMATCH

    pipeline.register(4, "numeric", numeric_layer, exclude_keys=frozenset({"numeric_samples"}))

    a = _token(
        {
            "repr": "x^2",
            "numeric_samples": [
                {"vars": {"x": 1.0}, "value": 1.0},
                {"vars": {"x": 2.0}, "value": 4.0},
            ],
        }
    )
    b = _token(
        {
            "repr": "x^2",
            "numeric_samples": [
                {"vars": {"x": 3.0}, "value": 9.0},
            ],
        }
    )
    result = pipeline.compare(a, b)
    assert result.status == TaskStatus.OK
    assert result.layer <= 2, "Should match at L1 or L2 after key exclusion"


def test_exclude_keys_one_side_missing():
    """L1/L2 match even if only one side has the excluded key."""
    pipeline = ComparisonPipeline()

    def numeric_layer(a: ValidationToken, b: ValidationToken) -> TaskStatus:
        return TaskStatus.MATH_MISMATCH

    pipeline.register(4, "numeric", numeric_layer, exclude_keys=frozenset({"numeric_samples"}))

    a = _token(
        {
            "repr": "x^2",
            "numeric_samples": [{"vars": {"x": 1.0}, "value": 1.0}],
        }
    )
    b = _token({"repr": "x^2"})
    result = pipeline.compare(a, b)
    assert result.status == TaskStatus.OK
    assert result.layer <= 2


def test_no_exclude_keys_backward_compat():
    """Registering a layer without exclude_keys works (no stripping)."""
    pipeline = ComparisonPipeline(default_layers=False)

    def always_ok(a: ValidationToken, b: ValidationToken) -> TaskStatus:
        return TaskStatus.OK

    pipeline.register(1, "custom", always_ok)
    a = _token({"x": 1})
    b = _token({"x": 1})
    result = pipeline.compare(a, b)
    assert result.status == TaskStatus.OK


def test_multi_layer_exclusion_union():
    """Exclusions from multiple higher layers are unioned."""
    pipeline = ComparisonPipeline(default_layers=False)
    dispatched = {}

    def l1(a: ValidationToken, b: ValidationToken) -> TaskStatus:
        dispatched["l1_a"] = a.result
        dispatched["l1_b"] = b.result
        return TaskStatus.OK

    def l3(a: ValidationToken, b: ValidationToken) -> TaskStatus:
        return TaskStatus.MATH_MISMATCH

    def l4(a: ValidationToken, b: ValidationToken) -> TaskStatus:
        return TaskStatus.MATH_MISMATCH

    pipeline.register(1, "identity", l1)
    pipeline.register(3, "canonical", l3, exclude_keys=frozenset({"canon_data"}))
    pipeline.register(4, "numeric", l4, exclude_keys=frozenset({"numeric_samples"}))

    a = _token({"repr": "x", "canon_data": [1], "numeric_samples": [2]})
    b = _token({"repr": "x", "canon_data": [3], "numeric_samples": [4]})
    result = pipeline.compare(a, b)
    assert result.status == TaskStatus.OK
    assert result.layer == 1
    # L1 should have received tokens without canon_data or numeric_samples
    assert "canon_data" not in dispatched["l1_a"]
    assert "numeric_samples" not in dispatched["l1_a"]
