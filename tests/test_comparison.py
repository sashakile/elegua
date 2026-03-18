"""Tests for Layer 1 identity comparison."""

from elegua.comparison import compare_identity
from elegua.models import ValidationToken
from elegua.task import TaskStatus


def _token(result: dict | None = None) -> ValidationToken:
    return ValidationToken(adapter_id="test", status=TaskStatus.OK, result=result)


def test_identical_results_return_ok():
    a = _token({"output": "T[a, b]", "hash": "abc123"})
    b = _token({"output": "T[a, b]", "hash": "abc123"})
    assert compare_identity(a, b) == TaskStatus.OK


def test_different_results_return_mismatch():
    a = _token({"output": "T[a, b]"})
    b = _token({"output": "T[b, a]"})
    assert compare_identity(a, b) == TaskStatus.MATH_MISMATCH


def test_empty_results_are_identical():
    a = _token({})
    b = _token({})
    assert compare_identity(a, b) == TaskStatus.OK


def test_nested_dicts():
    a = _token({"tensor": {"name": "T", "rank": 2}})
    b = _token({"tensor": {"name": "T", "rank": 2}})
    assert compare_identity(a, b) == TaskStatus.OK


def test_nested_dicts_differ():
    a = _token({"tensor": {"name": "T", "rank": 2}})
    b = _token({"tensor": {"name": "T", "rank": 3}})
    assert compare_identity(a, b) == TaskStatus.MATH_MISMATCH


def test_none_results_are_identical():
    a = _token(None)
    b = _token(None)
    assert compare_identity(a, b) == TaskStatus.OK
