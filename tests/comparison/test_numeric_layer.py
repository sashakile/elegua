"""Red-phase tests for the numeric comparison layer (elegua-1q3)."""

from __future__ import annotations

import pytest

pytest.importorskip(
    "elegua.numeric.layer",
    reason="elegua.numeric.layer not yet implemented (elegua-1q3)",
)

from elegua.comparison import ComparisonPipeline
from elegua.models import ValidationToken
from elegua.numeric.layer import NUMERIC_KEYS, make_numeric_layer
from elegua.numeric.tolerance import AbsoluteTolerance
from elegua.task import TaskStatus


def _token(result: dict | None) -> ValidationToken:
    return ValidationToken(adapter_id="test", status=TaskStatus.OK, result=result)


# --- Scalar routing ---


def test_numeric_layer_scalar_within_tolerance():
    layer = make_numeric_layer(strategy=AbsoluteTolerance(atol=1e-4))
    assert layer(_token({"value": 1.0}), _token({"value": 1.00005})) == TaskStatus.OK


def test_numeric_layer_scalar_outside_tolerance():
    layer = make_numeric_layer(strategy=AbsoluteTolerance(atol=1e-6))
    assert layer(_token({"value": 1.0}), _token({"value": 2.0})) == TaskStatus.MATH_MISMATCH


# --- Array routing ---


def test_numeric_layer_array_within_tolerance():
    layer = make_numeric_layer(strategy=AbsoluteTolerance(atol=1e-4))
    a = _token({"values": [1.0, 2.0, 3.0]})
    b = _token({"values": [1.00005, 2.0, 3.0]})
    assert layer(a, b) == TaskStatus.OK


def test_numeric_layer_array_outside_tolerance():
    layer = make_numeric_layer(strategy=AbsoluteTolerance(atol=1e-6))
    a = _token({"values": [1.0, 2.0, 3.0]})
    b = _token({"values": [1.0, 2.5, 3.0]})
    assert layer(a, b) == TaskStatus.MATH_MISMATCH


def test_numeric_layer_array_no_strategy_is_execution_error():
    layer = make_numeric_layer()
    a = _token({"values": [1.0, 2.0]})
    b = _token({"values": [1.0, 2.0]})
    assert layer(a, b) == TaskStatus.EXECUTION_ERROR


# --- Multi-sample routing ---


def test_numeric_layer_samples_within_tolerance():
    layer = make_numeric_layer(tol=1e-6)
    samples = [{"vars": {"x": 1.0}, "value": 0.3333}]
    tok = _token({"numeric_samples": samples})
    assert layer(tok, tok) == TaskStatus.OK


def test_numeric_layer_samples_outside_tolerance():
    layer = make_numeric_layer(tol=1e-6)
    a = _token({"numeric_samples": [{"vars": {"x": 1.0}, "value": 0.3333}]})
    b = _token({"numeric_samples": [{"vars": {"x": 1.0}, "value": 0.5000}]})
    assert layer(a, b) == TaskStatus.MATH_MISMATCH


# --- Non-numeric passthrough ---


def test_numeric_layer_non_numeric_returns_mismatch():
    layer = make_numeric_layer(strategy=AbsoluteTolerance(atol=1e-4))
    assert layer(_token({"repr": "x^2"}), _token({"repr": "x^2"})) == TaskStatus.MATH_MISMATCH


def test_numeric_layer_none_result_returns_mismatch():
    layer = make_numeric_layer(strategy=AbsoluteTolerance(atol=1e-4))
    assert layer(_token(None), _token(None)) == TaskStatus.MATH_MISMATCH


# --- Pipeline integration ---


def test_pipeline_l3_numeric_uses_value_field():
    """L3 numeric layer compares value fields; L1/L2 only see non-numeric keys."""
    pipeline = ComparisonPipeline()
    pipeline.register(
        3,
        "numeric",
        make_numeric_layer(strategy=AbsoluteTolerance(atol=1e-4)),
        exclude_keys=NUMERIC_KEYS,
    )
    a = _token({"repr": "x^2", "value": 1.0})
    b = _token({"repr": "x**2", "value": 1.00005})
    result = pipeline.compare(a, b)
    assert result.status == TaskStatus.OK
    assert result.layer == 3


def test_pipeline_existing_symbolic_fixtures_unaffected():
    """Fixtures without numeric fields are handled at L1/L2; L3 never reached."""
    pipeline = ComparisonPipeline()
    pipeline.register(
        3,
        "numeric",
        make_numeric_layer(strategy=AbsoluteTolerance(atol=1e-4)),
        exclude_keys=NUMERIC_KEYS,
    )
    a = _token({"repr": "x^2"})
    b = _token({"repr": "x^2"})
    result = pipeline.compare(a, b)
    assert result.status == TaskStatus.OK
    assert result.layer == 1


# --- NUMERIC_KEYS constant ---


def test_numeric_keys_contains_required_fields():
    required = {"value", "values", "numeric_samples", "quantity_label", "standard_error"}
    assert required.issubset(NUMERIC_KEYS)
    assert isinstance(NUMERIC_KEYS, frozenset)
