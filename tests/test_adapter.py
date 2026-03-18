"""Tests for Adapter ABC and WolframAdapter."""

from __future__ import annotations

import pytest

from elegua.adapter import Adapter, WolframAdapter
from elegua.models import ValidationToken
from elegua.task import EleguaTask, TaskStatus


def test_adapter_is_abstract():
    with pytest.raises(TypeError):
        Adapter()  # type: ignore[abstract]


def test_wolfram_adapter_is_adapter():
    adapter = WolframAdapter()
    assert isinstance(adapter, Adapter)


def test_wolfram_adapter_execute_returns_token():
    adapter = WolframAdapter()
    task = EleguaTask(action="DefTensor", payload={"name": "T", "indices": ["a", "b"]})
    token = adapter.execute(task)
    assert isinstance(token, ValidationToken)
    assert token.status in (TaskStatus.OK, TaskStatus.EXECUTION_ERROR)


def test_wolfram_adapter_stub_returns_ok():
    adapter = WolframAdapter()
    task = EleguaTask(action="DefTensor", payload={"name": "T"})
    token = adapter.execute(task)
    assert token.status == TaskStatus.OK
    assert token.result is not None
    assert token.adapter_id == "wolfram"


def test_adapter_id():
    adapter = WolframAdapter()
    assert adapter.adapter_id == "wolfram"


def test_execute_does_not_mutate_input():
    adapter = WolframAdapter()
    task = EleguaTask(action="DefTensor", payload={"name": "T"})
    adapter.execute(task)
    assert task.status == TaskStatus.PENDING
    assert task.result is None
