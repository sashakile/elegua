"""EleguaTask model, TaskStatus enum, and state machine transitions."""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from elegua.errors import EleguaError


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    OK = "ok"
    MATH_MISMATCH = "math_mismatch"
    EXECUTION_ERROR = "execution_error"
    TIMEOUT = "timeout"


# Valid state transitions: current_status → set of allowed next statuses
_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.PENDING: frozenset({TaskStatus.RUNNING}),
    TaskStatus.RUNNING: frozenset(
        {
            TaskStatus.OK,
            TaskStatus.MATH_MISMATCH,
            TaskStatus.EXECUTION_ERROR,
            TaskStatus.TIMEOUT,
        }
    ),
    # Terminal states — no transitions out
    TaskStatus.OK: frozenset(),
    TaskStatus.MATH_MISMATCH: frozenset(),
    TaskStatus.EXECUTION_ERROR: frozenset(),
    TaskStatus.TIMEOUT: frozenset(),
}


class InvalidTransition(EleguaError):
    """Raised when a task status transition is not allowed."""


class EleguaTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: str
    payload: dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    result: dict[str, Any] | None = None

    def transition(self, to: TaskStatus) -> EleguaTask:
        """Return a new task with the given status, enforcing the state machine.

        Raises InvalidTransition if the transition is not allowed.
        Does not mutate self.
        """
        allowed = _TRANSITIONS[self.status]
        if to not in allowed:
            raise InvalidTransition(f"Cannot transition from {self.status.name} to {to.name}")
        return self.model_copy(update={"status": to})
