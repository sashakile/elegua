"""Tests for the 4-Layer Comparison Pipeline."""

from __future__ import annotations

from elegua.comparison import (
    ComparisonResult,
    compare_identity,
    compare_structural,
    compare_pipeline,
)
from elegua.models import ValidationToken
from elegua.task import TaskStatus


def _token(result: dict | None = None) -> ValidationToken:
    return ValidationToken(adapter_id="test", status=TaskStatus.OK, result=result)


class TestLayer1Identity:
    def test_identical(self):
        a = _token({"x": 1})
        b = _token({"x": 1})
        assert compare_identity(a, b) == TaskStatus.OK

    def test_different(self):
        a = _token({"x": 1})
        b = _token({"x": 2})
        assert compare_identity(a, b) == TaskStatus.MATH_MISMATCH


class TestLayer2Structural:
    def test_identical_trees(self):
        a = _token({"fn": "Add", "args": [1, 2]})
        b = _token({"fn": "Add", "args": [1, 2]})
        assert compare_structural(a, b) == TaskStatus.OK

    def test_different_key_order_same_structure(self):
        """Dict key order shouldn't matter for structural comparison."""
        a = _token({"fn": "T", "args": [1], "rank": 2})
        b = _token({"rank": 2, "args": [1], "fn": "T"})
        assert compare_structural(a, b) == TaskStatus.OK

    def test_commutative_args(self):
        """Structural comparison detects reordered args as isomorphic via sorted canonical form."""
        a = _token({"fn": "Add", "args": [1, 2]})
        b = _token({"fn": "Add", "args": [2, 1]})
        assert compare_structural(a, b) == TaskStatus.OK

    def test_different_fn(self):
        a = _token({"fn": "Add", "args": [1, 2]})
        b = _token({"fn": "Mul", "args": [1, 2]})
        assert compare_structural(a, b) == TaskStatus.MATH_MISMATCH

    def test_different_arity(self):
        a = _token({"fn": "Add", "args": [1, 2]})
        b = _token({"fn": "Add", "args": [1, 2, 3]})
        assert compare_structural(a, b) == TaskStatus.MATH_MISMATCH

    def test_non_ast_dicts(self):
        """Non-AST dicts fall back to structural dict equality."""
        a = _token({"name": "T", "rank": 2})
        b = _token({"rank": 2, "name": "T"})
        assert compare_structural(a, b) == TaskStatus.OK


class TestPipeline:
    def test_identical_stops_at_layer1(self):
        a = _token({"x": 1})
        b = _token({"x": 1})
        result = compare_pipeline(a, b)
        assert result.status == TaskStatus.OK
        assert result.layer == 1

    def test_structural_match_stops_at_layer2(self):
        a = _token({"fn": "Add", "args": [1, 2]})
        b = _token({"fn": "Add", "args": [2, 1]})
        result = compare_pipeline(a, b)
        assert result.status == TaskStatus.OK
        assert result.layer == 2

    def test_mismatch_exhausts_all_layers(self):
        a = _token({"fn": "Add", "args": [1, 2]})
        b = _token({"fn": "Mul", "args": [3, 4]})
        result = compare_pipeline(a, b)
        assert result.status == TaskStatus.MATH_MISMATCH
        assert result.layer == 2  # last layer checked (no L3/L4 registered)

    def test_result_has_details(self):
        a = _token({"x": 1})
        b = _token({"x": 1})
        result = compare_pipeline(a, b)
        assert isinstance(result, ComparisonResult)
