"""Snapshot record/replay for offline CI.

Record: wrap an adapter with RecordingAdapter to capture all results.
Replay: use ReplayAdapter to serve cached results without an oracle.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from elegua.adapter import Adapter
from elegua.errors import SchemaError
from elegua.models import ValidationToken
from elegua.task import EleguaTask, TaskStatus


class SnapshotStore:
    """Persists and retrieves ValidationToken snapshots by content key."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path
        self._data: dict[str, dict[str, Any]] = {}

    @staticmethod
    def key(action: str, payload: dict[str, Any], adapter_id: str = "") -> str:
        """Compute deterministic key from adapter_id + action + payload."""
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        canonical = adapter_id + "|" + action + "|" + payload_json
        return hashlib.sha256(canonical.encode()).hexdigest()

    def save(self, key: str, token: ValidationToken) -> None:
        """Store a token under the given key."""
        self._data[key] = token.model_dump()

    def load(self, key: str) -> ValidationToken | None:
        """Retrieve a token by key, or None if not found."""
        raw = self._data.get(key)
        if raw is None:
            return None
        return ValidationToken.model_validate(raw)

    def __len__(self) -> int:
        return len(self._data)

    def write(self) -> None:
        """Persist all snapshots to disk as JSON."""
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({"snapshots": self._data}, indent=2, sort_keys=True) + "\n"
        )

    @classmethod
    def read(cls, path: Path) -> SnapshotStore:
        """Load a snapshot store from disk. Returns empty store if file missing."""
        store = cls(path)
        if path.exists():
            try:
                raw = json.loads(path.read_text())
            except json.JSONDecodeError as exc:
                raise SchemaError(f"{path}: corrupt snapshot JSON: {exc}") from exc
            if not isinstance(raw, dict):
                raise SchemaError(f"{path}: expected JSON object, got {type(raw).__name__}")
            store._data = raw.get("snapshots", {})
        return store


class RecordingAdapter(Adapter):
    """Wraps an adapter and records all results to a SnapshotStore."""

    def __init__(self, inner: Adapter, store: SnapshotStore) -> None:
        self._inner = inner
        self._store = store

    @property
    def adapter_id(self) -> str:
        return self._inner.adapter_id

    def initialize(self) -> None:
        self._inner.initialize()

    def teardown(self) -> None:
        self._inner.teardown()
        self._store.write()

    def execute(self, task: EleguaTask) -> ValidationToken:
        token = self._inner.execute(task)
        key = SnapshotStore.key(task.action, task.payload, self._inner.adapter_id)
        self._store.save(key, token)
        return token


class ReplayAdapter(Adapter):
    """Serves cached results from a SnapshotStore. No oracle needed.

    The ``original_adapter_id`` parameter controls which adapter's snapshots
    are looked up. This defaults to the replay adapter's own identity but
    should be set to the adapter_id used during recording when replaying
    snapshots recorded by a different adapter.
    """

    def __init__(self, store: SnapshotStore, original_adapter_id: str | None = None) -> None:
        self._store = store
        self._original_adapter_id = original_adapter_id

    @property
    def adapter_id(self) -> str:
        return "replay"

    def execute(self, task: EleguaTask) -> ValidationToken:
        key_adapter = (
            self._original_adapter_id if self._original_adapter_id is not None else self.adapter_id
        )
        key = SnapshotStore.key(task.action, task.payload, key_adapter)
        token = self._store.load(key)
        if token is None:
            return ValidationToken(
                adapter_id=self.adapter_id,
                status=TaskStatus.EXECUTION_ERROR,
                metadata={"error": f"No snapshot for {task.action}"},
            )
        return token
