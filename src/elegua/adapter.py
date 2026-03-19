"""Adapter ABC and WolframAdapter stub for tracer bullet."""

from __future__ import annotations

import abc
from typing import Self

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
        self.teardown()


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
