"""Tests for Adapter ABC and WolframAdapter."""

from __future__ import annotations

import pytest

from elegua.adapter import Adapter, WolframAdapter
from elegua.task import EleguaTask, TaskStatus


def test_adapter_is_abstract():
    with pytest.raises(TypeError):
        Adapter()  # type: ignore[abstract]


def test_wolfram_adapter_is_adapter():
    adapter = WolframAdapter()
    assert isinstance(adapter, Adapter)


def test_wolfram_adapter_execute_returns_task():
    adapter = WolframAdapter()
    task = EleguaTask(action="DefTensor", payload={"name": "T", "indices": ["a", "b"]})
    result = adapter.execute(task)
    assert isinstance(result, EleguaTask)
    assert result.status in (TaskStatus.OK, TaskStatus.EXECUTION_ERROR)


def test_wolfram_adapter_stub_returns_ok():
    """The stub WolframAdapter echoes payload as result for the tracer."""
    adapter = WolframAdapter()
    task = EleguaTask(action="DefTensor", payload={"name": "T"})
    result = adapter.execute(task)
    assert result.status == TaskStatus.OK
    assert result.result is not None


def test_adapter_id():
    adapter = WolframAdapter()
    assert adapter.adapter_id == "wolfram"


def test_execute_does_not_mutate_input():
    """Adapter.execute() must return a new task, not mutate the input."""
    adapter = WolframAdapter()
    task = EleguaTask(action="DefTensor", payload={"name": "T"})
    result = adapter.execute(task)
    assert result is not task
    assert task.status == TaskStatus.PENDING
    assert task.result is None
