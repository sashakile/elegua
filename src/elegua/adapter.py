"""Adapter ABC and WolframAdapter stub for tracer bullet."""

from __future__ import annotations

import abc

from elegua.task import EleguaTask, TaskStatus


class Adapter(abc.ABC):
    @property
    @abc.abstractmethod
    def adapter_id(self) -> str: ...

    @abc.abstractmethod
    def execute(self, task: EleguaTask) -> EleguaTask:
        """Execute the task and return a new EleguaTask with status and result.

        Implementations MUST NOT mutate the input task. Return a copy via
        task.model_copy(update={...}).
        """
        ...


class WolframAdapter(Adapter):
    """Stub adapter that echoes payload as result.

    The real implementation will send actions to a Dockerized Wolfram kernel
    via subprocess/ZMQ. For the tracer bullet, we just echo to prove the
    architecture works end-to-end.
    """

    @property
    def adapter_id(self) -> str:
        return "wolfram"

    def execute(self, task: EleguaTask) -> EleguaTask:
        return task.model_copy(update={
            "status": TaskStatus.OK,
            "result": {"adapter": self.adapter_id, **task.payload},
        })
