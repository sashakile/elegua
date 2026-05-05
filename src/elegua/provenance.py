"""Provenance records for ValidationTokens."""

from __future__ import annotations

import datetime
from typing import Any

from pydantic import BaseModel

from elegua.models import ValidationToken


class ProvenanceRecord(BaseModel):
    fixture_id: str
    fixture_content_hash: str
    adapter_id: str
    adapter_version: str
    elegua_version: str
    timestamp: datetime.datetime
    environment_hash: str
    duration: float
    host: str
    git_sha: str | None = None
    seed: int | None = None


def attach_provenance(token: ValidationToken, record: ProvenanceRecord) -> ValidationToken:
    """Return a new token with provenance data merged into metadata."""
    provenance: dict[str, Any] = {
        "fixture_id": record.fixture_id,
        "fixture_content_hash": record.fixture_content_hash,
        "adapter_id": record.adapter_id,
        "adapter_version": record.adapter_version,
        "elegua_version": record.elegua_version,
        "timestamp": record.timestamp.isoformat(),
        "environment_hash": record.environment_hash,
        "duration": record.duration,
        "host": record.host,
        "git_sha": record.git_sha,
        "seed": record.seed,
    }
    new_metadata = {**token.metadata, "provenance": provenance}
    return token.model_copy(update={"metadata": new_metadata})
