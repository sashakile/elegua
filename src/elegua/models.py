"""ActionPayload and ValidationToken — the spec-defined interchange models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from elegua.task import TaskStatus


class ActionPayload(BaseModel):
    """Input to an adapter. See spec §1.1."""

    action: str
    payload: dict[str, Any]
    domain: str | None = None
    manifest: str | None = None


class ValidationToken(BaseModel):
    """Output from an adapter. See spec §1.2."""

    adapter_id: str
    status: TaskStatus
    result: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
