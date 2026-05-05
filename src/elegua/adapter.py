"""Adapter ABC and WolframAdapter stub for tracer bullet."""

from __future__ import annotations

import abc
from typing import Self

from elegua.errors import IsolationError
from elegua.models import ValidationToken
from elegua.task import EleguaTask, TaskStatus


class Adapter(abc.ABC):
    @property
    @abc.abstractmethod
    def adapter_id(self) -> str: ...

    def initialize(self) -> None:  # noqa: B027
        """Set up adapter resources (kernel, connection, etc.).

        Default is a no-op. Override in subclasses that manage
        external processes or connections.
        """

    def teardown(self) -> None:  # noqa: B027
        """Release adapter resources.

        Default is a no-op. Override in subclasses. Must not raise
        even if the adapter is in an error state.
        """

    @abc.abstractmethod
    def execute(self, task: EleguaTask) -> ValidationToken:
        """Execute the task and return a ValidationToken.

        Implementations MUST NOT mutate the input task.
        """
        ...

    def __enter__(self) -> Self:
        self.initialize()
        return self

    def __exit__(self, *_: object) -> None:
        try:
            self.teardown()
        except Exception:
            import warnings

            msg = (
                f"{type(self).__name__}.teardown() raised; "
                "suppressing to preserve original exception"
            )
            warnings.warn(msg, RuntimeWarning, stacklevel=2)


_ISOLATION_PROBE_TASK = EleguaTask(action="__isolation_probe__", payload={})


def verify_isolation(adapter: Adapter, task: EleguaTask | None = None) -> None:
    """Raise IsolationError if the adapter produces different results on repeated calls."""
    probe = task if task is not None else _ISOLATION_PROBE_TASK
    r1 = adapter.execute(probe)
    r2 = adapter.execute(probe)
    if r1.result != r2.result or r1.status != r2.status:
        raise IsolationError(
            f"Adapter {adapter.adapter_id!r} shows state leakage between executions"
        )


class WolframAdapter(Adapter):
    """Stub adapter that echoes payload as result.

    The real implementation will send actions to a Dockerized Wolfram kernel
    via subprocess/ZMQ. For the tracer bullet, we just echo to prove the
    architecture works end-to-end.
    """

    @property
    def adapter_id(self) -> str:
        return "wolfram"

    def execute(self, task: EleguaTask) -> ValidationToken:
        return ValidationToken(
            adapter_id=self.adapter_id,
            status=TaskStatus.OK,
            result=task.payload,
        )
