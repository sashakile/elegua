"""EleguaTask model and TaskStatus enum."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    OK = "ok"
    MATH_MISMATCH = "math_mismatch"
    EXECUTION_ERROR = "execution_error"
    TIMEOUT = "timeout"


class EleguaTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: str
    payload: dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    result: dict[str, Any] | None = None
