"""SHA-256 Blob Store for large payloads.

Payloads exceeding 1MB are stored by content hash in a two-level directory
structure: .elegua/blobs/[ab]/[cd...] where [ab] is the first two hex chars
and [cd...] is the remainder of the SHA-256 hex digest.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from elegua.errors import SchemaError

ONE_MB = 1024 * 1024


class BlobStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _hash(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _blob_path(self, sha: str) -> Path:
        return self.root / sha[:2] / sha[2:]

    def _serialize(self, payload: dict[str, Any]) -> bytes:
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    def put(self, payload: dict[str, Any]) -> dict[str, str]:
        """Store payload and return a blob reference {"blob": "<sha256>"}."""
        data = self._serialize(payload)
        sha = self._hash(data)
        path = self._blob_path(sha)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return {"blob": sha}

    def get(self, sha: str) -> dict[str, Any]:
        """Retrieve payload by SHA-256 hash. Raises FileNotFoundError if missing."""
        path = self._blob_path(sha)
        data = path.read_bytes()
        try:
            return json.loads(data)
        except json.JSONDecodeError as exc:
            raise SchemaError(f"Corrupt blob {sha[:12]}... at {path}: {exc}") from exc

    def should_store(self, payload: dict[str, Any]) -> bool:
        """Return True if payload exceeds the 1MB threshold."""
        return len(self._serialize(payload)) > ONE_MB

    def maybe_store(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Store if large, return blob ref; otherwise return payload unchanged."""
        if self.should_store(payload):
            return self.put(payload)
        return payload

    def maybe_resolve(self, payload: dict[str, Any]) -> dict[str, Any]:
        """If payload is a blob ref, resolve it; otherwise return as-is."""
        if set(payload.keys()) == {"blob"} and isinstance(payload.get("blob"), str):
            return self.get(payload["blob"])
        return payload
