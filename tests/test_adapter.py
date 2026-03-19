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


# --- Lifecycle: initialize / teardown ---


def test_default_initialize_is_noop():
    adapter = WolframAdapter()
    result = adapter.initialize()
    assert result is None


def test_default_teardown_is_noop():
    adapter = WolframAdapter()
    result = adapter.teardown()
    assert result is None


def test_adapter_works_without_lifecycle_calls():
    """Backward compat: execute still works without calling initialize/teardown."""
    adapter = WolframAdapter()
    task = EleguaTask(action="DefTensor", payload={"name": "T"})
    token = adapter.execute(task)
    assert token.status == TaskStatus.OK


def test_lifecycle_bracket():
    """initialize → execute → teardown full lifecycle."""
    adapter = WolframAdapter()
    adapter.initialize()
    task = EleguaTask(action="DefTensor", payload={"name": "T"})
    token = adapter.execute(task)
    adapter.teardown()
    assert token.status == TaskStatus.OK


def test_context_manager():
    """Adapter can be used as a context manager."""
    with WolframAdapter() as adapter:
        task = EleguaTask(action="DefTensor", payload={"name": "T"})
        token = adapter.execute(task)
        assert token.status == TaskStatus.OK


def test_custom_adapter_lifecycle():
    """Custom adapter can override initialize and teardown."""

    class TrackingAdapter(Adapter):
        def __init__(self):
            self.initialized = False
            self.torn_down = False

        @property
        def adapter_id(self) -> str:
            return "tracking"

        def initialize(self) -> None:
            self.initialized = True

        def teardown(self) -> None:
            self.torn_down = True

        def execute(self, task: EleguaTask) -> ValidationToken:
            return ValidationToken(
                adapter_id=self.adapter_id,
                status=TaskStatus.OK,
                result=task.payload,
            )

    adapter = TrackingAdapter()
    assert not adapter.initialized
    adapter.initialize()
    assert adapter.initialized
    task = EleguaTask(action="Test", payload={})
    adapter.execute(task)
    adapter.teardown()
    assert adapter.torn_down


def test_context_manager_calls_lifecycle():
    """Context manager calls initialize on enter and teardown on exit."""

    class TrackingAdapter(Adapter):
        def __init__(self):
            self.initialized = False
            self.torn_down = False

        @property
        def adapter_id(self) -> str:
            return "tracking"

        def initialize(self) -> None:
            self.initialized = True

        def teardown(self) -> None:
            self.torn_down = True

        def execute(self, task: EleguaTask) -> ValidationToken:
            return ValidationToken(
                adapter_id=self.adapter_id,
                status=TaskStatus.OK,
                result=task.payload,
            )

    adapter = TrackingAdapter()
    assert not adapter.initialized
    with adapter:
        assert adapter.initialized
        assert not adapter.torn_down
    assert adapter.torn_down


def test_context_manager_teardown_on_exception():
    """Teardown is called even if execute raises."""

    class FailingAdapter(Adapter):
        def __init__(self):
            self.torn_down = False

        @property
        def adapter_id(self) -> str:
            return "failing"

        def teardown(self) -> None:
            self.torn_down = True

        def execute(self, task: EleguaTask) -> ValidationToken:
            raise RuntimeError("boom")

    adapter = FailingAdapter()
    with pytest.raises(RuntimeError, match="boom"), adapter:
        adapter.execute(EleguaTask(action="Test", payload={}))
    assert adapter.torn_down


# --- Teardown exception guarding (M5) ---


def test_teardown_exception_suppressed_with_warning():
    """If teardown() raises, the warning is emitted but the original exception propagates."""

    class BadTeardown(Adapter):
        @property
        def adapter_id(self) -> str:
            return "bad"

        def execute(self, task: EleguaTask) -> ValidationToken:
            return ValidationToken(
                adapter_id=self.adapter_id,
                status=TaskStatus.OK,
                result={},
            )

        def teardown(self) -> None:
            raise RuntimeError("teardown boom")

    adapter = BadTeardown()
    with pytest.warns(RuntimeWarning, match=r"teardown.*raised"), adapter:
        pass  # normal exit, teardown will raise


def test_teardown_does_not_mask_original_exception():
    """Original exception propagates even when teardown also raises."""

    class BadTeardown(Adapter):
        @property
        def adapter_id(self) -> str:
            return "bad"

        def execute(self, task: EleguaTask) -> ValidationToken:
            raise ValueError("exec error")

        def teardown(self) -> None:
            raise RuntimeError("teardown boom")

    adapter = BadTeardown()
    with (
        pytest.warns(RuntimeWarning),
        pytest.raises(ValueError, match="exec error"),
        adapter,
    ):
        adapter.execute(None)
