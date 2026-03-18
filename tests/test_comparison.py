"""Tests for Layer 1 identity comparison."""

from elegua.comparison import compare_identity
from elegua.task import TaskStatus


def test_identical_results_return_ok():
    result_a = {"output": "T[a, b]", "hash": "abc123"}
    result_b = {"output": "T[a, b]", "hash": "abc123"}
    assert compare_identity(result_a, result_b) == TaskStatus.OK


def test_different_results_return_mismatch():
    result_a = {"output": "T[a, b]"}
    result_b = {"output": "T[b, a]"}
    assert compare_identity(result_a, result_b) == TaskStatus.MATH_MISMATCH


def test_empty_dicts_are_identical():
    assert compare_identity({}, {}) == TaskStatus.OK


def test_nested_dicts():
    result_a = {"tensor": {"name": "T", "rank": 2}}
    result_b = {"tensor": {"name": "T", "rank": 2}}
    assert compare_identity(result_a, result_b) == TaskStatus.OK


def test_nested_dicts_differ():
    result_a = {"tensor": {"name": "T", "rank": 2}}
    result_b = {"tensor": {"name": "T", "rank": 3}}
    assert compare_identity(result_a, result_b) == TaskStatus.MATH_MISMATCH
