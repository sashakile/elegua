"""Tests for EleguaTask model and TaskStatus enum."""

from elegua.task import EleguaTask, TaskStatus


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
