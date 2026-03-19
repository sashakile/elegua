"""Tests for EleguaTask model and TaskStatus enum."""

import pytest

from elegua.task import EleguaTask, InvalidTransition, TaskStatus


def test_task_status_values():
    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.RUNNING.value == "running"
    assert TaskStatus.OK.value == "ok"
    assert TaskStatus.MATH_MISMATCH.value == "math_mismatch"
    assert TaskStatus.EXECUTION_ERROR.value == "execution_error"
    assert TaskStatus.TIMEOUT.value == "timeout"


def test_task_defaults():
    task = EleguaTask(action="DefTensor", payload={"name": "T"})
    assert task.status == TaskStatus.PENDING
    assert task.id is not None
    assert task.action == "DefTensor"
    assert task.payload == {"name": "T"}


def test_task_explicit_status():
    task = EleguaTask(
        action="Contract",
        payload={"expr": "T[a,b]"},
        status=TaskStatus.OK,
    )
    assert task.status == TaskStatus.OK


def test_task_result_field():
    task = EleguaTask(action="DefTensor", payload={})
    assert task.result is None
    task.result = {"output": "done"}
    assert task.result == {"output": "done"}


# --- State machine transitions ---


def test_transition_pending_to_running():
    task = EleguaTask(action="Foo", payload={})
    new = task.transition(TaskStatus.RUNNING)
    assert new.status == TaskStatus.RUNNING


def test_transition_running_to_ok():
    task = EleguaTask(action="Foo", payload={}, status=TaskStatus.RUNNING)
    new = task.transition(TaskStatus.OK)
    assert new.status == TaskStatus.OK


def test_transition_running_to_math_mismatch():
    task = EleguaTask(action="Foo", payload={}, status=TaskStatus.RUNNING)
    new = task.transition(TaskStatus.MATH_MISMATCH)
    assert new.status == TaskStatus.MATH_MISMATCH


def test_transition_running_to_execution_error():
    task = EleguaTask(action="Foo", payload={}, status=TaskStatus.RUNNING)
    new = task.transition(TaskStatus.EXECUTION_ERROR)
    assert new.status == TaskStatus.EXECUTION_ERROR


def test_transition_running_to_timeout():
    task = EleguaTask(action="Foo", payload={}, status=TaskStatus.RUNNING)
    new = task.transition(TaskStatus.TIMEOUT)
    assert new.status == TaskStatus.TIMEOUT


def test_transition_invalid_pending_to_ok():
    task = EleguaTask(action="Foo", payload={})
    with pytest.raises(InvalidTransition, match=r"PENDING.*OK"):
        task.transition(TaskStatus.OK)


def test_transition_invalid_from_terminal_ok():
    task = EleguaTask(action="Foo", payload={}, status=TaskStatus.OK)
    with pytest.raises(InvalidTransition):
        task.transition(TaskStatus.RUNNING)


def test_transition_invalid_from_terminal_math_mismatch():
    task = EleguaTask(action="Foo", payload={}, status=TaskStatus.MATH_MISMATCH)
    with pytest.raises(InvalidTransition):
        task.transition(TaskStatus.RUNNING)


def test_transition_invalid_from_terminal_execution_error():
    task = EleguaTask(action="Foo", payload={}, status=TaskStatus.EXECUTION_ERROR)
    with pytest.raises(InvalidTransition):
        task.transition(TaskStatus.PENDING)


def test_transition_invalid_from_terminal_timeout():
    task = EleguaTask(action="Foo", payload={}, status=TaskStatus.TIMEOUT)
    with pytest.raises(InvalidTransition):
        task.transition(TaskStatus.OK)


def test_transition_self_pending():
    """Self-transition PENDING->PENDING is not allowed."""
    task = EleguaTask(action="Foo", payload={})
    with pytest.raises(InvalidTransition):
        task.transition(TaskStatus.PENDING)


def test_transition_does_not_mutate():
    """transition() returns a new task without modifying the original."""
    task = EleguaTask(action="Foo", payload={})
    new = task.transition(TaskStatus.RUNNING)
    assert task.status == TaskStatus.PENDING  # original unchanged
    assert new.status == TaskStatus.RUNNING
    assert task.id == new.id  # same task identity


def test_transition_preserves_fields():
    """transition() preserves action, payload, result, and id."""
    task = EleguaTask(action="Bar", payload={"x": 1}, result={"y": 2})
    new = task.transition(TaskStatus.RUNNING)
    assert new.action == "Bar"
    assert new.payload == {"x": 1}
    assert new.result == {"y": 2}
    assert new.id == task.id


# --- All statuses have transitions (L4) ---


def test_all_statuses_have_transitions():
    """Every TaskStatus enum value must have an entry in _TRANSITIONS."""
    from elegua.task import _TRANSITIONS, TaskStatus

    for status in TaskStatus:
        assert status in _TRANSITIONS, f"Missing transition entry for {status}"
