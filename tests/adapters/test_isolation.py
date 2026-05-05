"""Red-phase tests for verify_isolation helper.

All tests in this file MUST FAIL until verify_isolation is implemented.
See: elegua-sgvn, elegua-6igp.
"""

from __future__ import annotations

import pytest

from elegua.adapter import Adapter, verify_isolation
from elegua.errors import IsolationError
from elegua.models import ValidationToken
from elegua.task import EleguaTask, TaskStatus


class StatelessAdapter(Adapter):
    """Always returns the same result for the same input (no state leakage)."""

    @property
    def adapter_id(self) -> str:
        return "stateless"

    def execute(self, task: EleguaTask) -> ValidationToken:
        return ValidationToken(
            adapter_id=self.adapter_id,
            status=TaskStatus.OK,
            result={"value": task.payload.get("x", 0)},
        )


class StatefulAdapter(Adapter):
    """Accumulates state: result depends on call history, not just input."""

    def __init__(self) -> None:
        self._call_count = 0

    @property
    def adapter_id(self) -> str:
        return "stateful"

    def execute(self, task: EleguaTask) -> ValidationToken:
        self._call_count += 1
        return ValidationToken(
            adapter_id=self.adapter_id,
            status=TaskStatus.OK,
            # Result changes on each call — state leakage
            result={"value": task.payload.get("x", 0) + self._call_count},
        )


class DeterministicButSlowAdapter(Adapter):
    """Stateless adapter — returns deterministic results."""

    @property
    def adapter_id(self) -> str:
        return "deterministic"

    def execute(self, task: EleguaTask) -> ValidationToken:
        x = task.payload.get("x", 0)
        return ValidationToken(
            adapter_id=self.adapter_id,
            status=TaskStatus.OK,
            result={"value": x * 2},
        )


# --- Stateless adapter passes verification ---


def test_verify_isolation_passes_for_stateless_adapter():
    adapter = StatelessAdapter()
    task = EleguaTask(action="eval", payload={"x": 1.0})
    # Must not raise
    verify_isolation(adapter, task)


def test_verify_isolation_passes_for_deterministic_adapter():
    adapter = DeterministicButSlowAdapter()
    task = EleguaTask(action="eval", payload={"x": 5.0})
    verify_isolation(adapter, task)


# --- Stateful adapter raises IsolationError ---


def test_verify_isolation_raises_for_stateful_adapter():
    adapter = StatefulAdapter()
    task = EleguaTask(action="eval", payload={"x": 0.0})
    with pytest.raises(IsolationError):
        verify_isolation(adapter, task)


def test_isolation_error_is_elegua_error():
    from elegua.errors import EleguaError

    assert issubclass(IsolationError, EleguaError)


# --- IsolationError carries adapter identity ---


def test_isolation_error_identifies_adapter():
    adapter = StatefulAdapter()
    task = EleguaTask(action="eval", payload={"x": 0.0})
    with pytest.raises(IsolationError, match="stateful"):
        verify_isolation(adapter, task)


# --- verify_isolation uses a default task when none is provided ---


def test_verify_isolation_works_without_explicit_task():
    adapter = StatelessAdapter()
    # Must not raise with no task argument (uses a synthetic default)
    verify_isolation(adapter)


def test_verify_isolation_stateful_raises_without_explicit_task():
    adapter = StatefulAdapter()
    with pytest.raises(IsolationError):
        verify_isolation(adapter)
