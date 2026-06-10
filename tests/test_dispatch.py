"""Red-phase tests for parallel dispatch, partial failure, and bounded pools (elegua-exgo).

These tests define the contract for the future ``elegua.dispatch`` module.
They should fail until elegua-dfm5 is implemented.
"""

from __future__ import annotations

import pytest

pytest.importorskip(
    "elegua.dispatch",
    reason="elegua.dispatch not yet implemented (elegua-dfm5)",
)

from elegua.adapter import Adapter
from elegua.dispatch import AdapterPool, DispatchResult, dispatch_parallel
from elegua.models import ValidationToken
from elegua.task import EleguaTask, TaskStatus

# --- Toy adapters ---


class _OkAdapter(Adapter):
    def __init__(self, aid: str = "ok") -> None:
        self._id = aid
        self.reset_count = 0
        self.close_count = 0

    @property
    def adapter_id(self) -> str:
        return self._id

    def execute(self, task: EleguaTask) -> ValidationToken:
        return ValidationToken(
            adapter_id=self._id,
            status=TaskStatus.OK,
            result={"value": 1},
        )

    def reset(self) -> None:
        # reset() is not yet in Adapter ABC; this test defines the contract
        # that AdapterPool must call reset() between task executions.
        self.reset_count += 1

    def teardown(self) -> None:
        self.close_count += 1


class _FailingAdapter(Adapter):
    @property
    def adapter_id(self) -> str:
        return "failing"

    def execute(self, task: EleguaTask) -> ValidationToken:
        raise RuntimeError("adapter exploded")

    def teardown(self) -> None:
        pass


_TASK = EleguaTask(action="expand", payload={"expr": "x^2"})


# --- Parallel dispatch ---


def test_dispatch_parallel_returns_result_for_every_adapter():
    adapters = [_OkAdapter("a"), _OkAdapter("b")]
    results = dispatch_parallel(adapters, _TASK)
    assert len(results) == 2
    assert all(isinstance(r, DispatchResult) for r in results)


def test_dispatch_parallel_all_adapters_complete_before_return():
    adapters = [_OkAdapter("a"), _OkAdapter("b")]
    results = dispatch_parallel(adapters, _TASK)
    ids = {r.adapter_id for r in results}
    assert ids == {"a", "b"}


def test_dispatch_parallel_successful_result_has_token():
    results = dispatch_parallel([_OkAdapter()], _TASK)
    assert results[0].token is not None
    assert results[0].token.status == TaskStatus.OK
    assert results[0].error is None


# --- Partial failure ---


def test_partial_failure_reports_both_results():
    adapters = [_OkAdapter("ok"), _FailingAdapter()]
    results = dispatch_parallel(adapters, _TASK)
    assert len(results) == 2


def test_partial_failure_failed_adapter_has_error():
    adapters = [_OkAdapter("ok"), _FailingAdapter()]
    results = dispatch_parallel(adapters, _TASK)
    by_id = {r.adapter_id: r for r in results}
    assert by_id["failing"].error is not None
    assert by_id["failing"].token is None


def test_partial_failure_success_adapter_still_has_token():
    adapters = [_OkAdapter("ok"), _FailingAdapter()]
    results = dispatch_parallel(adapters, _TASK)
    by_id = {r.adapter_id: r for r in results}
    assert by_id["ok"].token is not None
    assert by_id["ok"].error is None


# --- Bounded pool ---


def test_pool_respects_max_size():
    pool = AdapterPool(factory=_OkAdapter, max_size=2)
    a1 = pool.acquire()
    a2 = pool.acquire()
    assert pool.active_count == 2
    # Third acquire must raise a pool-exhausted error when at max capacity
    with pytest.raises((RuntimeError, TimeoutError), match=r"(?i)(pool|exhausted|timeout|full)"):
        pool.acquire(timeout=0)
    pool.release(a1)
    pool.release(a2)
    pool.close()


def test_pool_reset_is_called_between_task_executions():
    adapter = _OkAdapter("pooled")
    pool = AdapterPool(factory=lambda: adapter, max_size=1)
    acquired = pool.acquire()
    pool.release(acquired)
    acquired2 = pool.acquire()
    # reset() must be called exactly once per release/re-acquire cycle
    assert adapter.reset_count == 1
    pool.release(acquired2)
    pool.close()


def test_pool_close_tears_down_all_adapters():
    # Intentionally tests close() while an adapter is still checked out —
    # close() must forcefully teardown unreleased adapters.
    adapter = _OkAdapter("pooled")
    pool = AdapterPool(factory=lambda: adapter, max_size=1)
    pool.acquire()
    pool.close()
    assert adapter.close_count >= 1
