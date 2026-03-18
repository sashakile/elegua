"""Tests for EleguaTask state machine transitions."""

from __future__ import annotations

import pytest

from elegua.task import EleguaTask, TaskStatus, InvalidTransition


def test_valid_transition_pending_to_running():
    task = EleguaTask(action="DefTensor", payload={})
    updated = task.transition(TaskStatus.RUNNING)
    assert updated.status == TaskStatus.RUNNING
    assert task.status == TaskStatus.PENDING  # original unchanged


def test_valid_transition_running_to_ok():
    task = EleguaTask(action="DefTensor", payload={}, status=TaskStatus.RUNNING)
    updated = task.transition(TaskStatus.OK)
    assert updated.status == TaskStatus.OK


def test_valid_transition_running_to_math_mismatch():
    task = EleguaTask(action="DefTensor", payload={}, status=TaskStatus.RUNNING)
    updated = task.transition(TaskStatus.MATH_MISMATCH)
    assert updated.status == TaskStatus.MATH_MISMATCH


def test_valid_transition_running_to_execution_error():
    task = EleguaTask(action="DefTensor", payload={}, status=TaskStatus.RUNNING)
    updated = task.transition(TaskStatus.EXECUTION_ERROR)
    assert updated.status == TaskStatus.EXECUTION_ERROR


def test_valid_transition_running_to_timeout():
    task = EleguaTask(action="DefTensor", payload={}, status=TaskStatus.RUNNING)
    updated = task.transition(TaskStatus.TIMEOUT)
    assert updated.status == TaskStatus.TIMEOUT


def test_invalid_transition_pending_to_ok():
    task = EleguaTask(action="DefTensor", payload={})
    with pytest.raises(InvalidTransition, match="PENDING.*OK"):
        task.transition(TaskStatus.OK)


def test_invalid_transition_ok_to_running():
    task = EleguaTask(action="DefTensor", payload={}, status=TaskStatus.OK)
    with pytest.raises(InvalidTransition):
        task.transition(TaskStatus.RUNNING)


def test_invalid_transition_error_to_ok():
    task = EleguaTask(action="DefTensor", payload={}, status=TaskStatus.EXECUTION_ERROR)
    with pytest.raises(InvalidTransition):
        task.transition(TaskStatus.OK)


def test_transition_does_not_mutate():
    task = EleguaTask(action="DefTensor", payload={})
    updated = task.transition(TaskStatus.RUNNING)
    assert updated is not task
    assert task.status == TaskStatus.PENDING
