"""Tests for SHA-256 Blob Store."""

from __future__ import annotations

from pathlib import Path

import pytest

from elegua.blobstore import BlobStore
from elegua.errors import SchemaError

ONE_MB = 1024 * 1024


@pytest.fixture
def store(tmp_path: Path) -> BlobStore:
    return BlobStore(root=tmp_path / "blobs")


class TestBlobStore:
    def test_store_and_retrieve(self, store: BlobStore):
        data = {"large": "x" * (ONE_MB + 1)}
        ref = store.put(data)
        assert "blob" in ref
        assert isinstance(ref["blob"], str)
        assert len(ref["blob"]) == 64  # SHA-256 hex

        retrieved = store.get(ref["blob"])
        assert retrieved == data

    def test_two_level_directory(self, store: BlobStore):
        data = {"key": "value" * 200_000}
        ref = store.put(data)
        sha = ref["blob"]
        expected_path = store.root / sha[:2] / sha[2:]
        assert expected_path.exists()

    def test_deterministic_hash(self, store: BlobStore):
        data = {"deterministic": True}
        ref1 = store.put(data)
        ref2 = store.put(data)
        assert ref1["blob"] == ref2["blob"]

    def test_get_missing_blob(self, store: BlobStore):
        with pytest.raises(FileNotFoundError):
            store.get("0" * 64)

    def test_should_store(self, store: BlobStore):
        small = {"x": 1}
        large = {"x": "a" * (ONE_MB + 1)}
        assert not store.should_store(small)
        assert store.should_store(large)

    def test_maybe_store_small_payload_passthrough(self, store: BlobStore):
        data = {"x": 1}
        result = store.maybe_store(data)
        assert result == data  # unchanged, no blob ref

    def test_maybe_store_large_payload_returns_ref(self, store: BlobStore):
        data = {"x": "a" * (ONE_MB + 1)}
        result = store.maybe_store(data)
        assert "blob" in result
        assert len(result) == 1  # only the blob ref

    def test_maybe_resolve_plain_dict(self, store: BlobStore):
        data = {"x": 1}
        assert store.maybe_resolve(data) == data

    def test_maybe_resolve_blob_ref(self, store: BlobStore):
        data = {"x": "a" * (ONE_MB + 1)}
        ref = store.maybe_store(data)
        resolved = store.maybe_resolve(ref)
        assert resolved == data

    def test_maybe_resolve_blob_key_plus_extra_keys_not_treated_as_ref(self, store: BlobStore):
        """A dict with 'blob' plus other keys is NOT a blob reference."""
        data = {"blob": "abc123", "extra": "data"}
        assert store.maybe_resolve(data) == data

    def test_maybe_resolve_non_string_blob_value_not_treated_as_ref(self, store: BlobStore):
        """A dict with blob=<non-string> is NOT a blob reference."""
        data = {"blob": 12345}
        assert store.maybe_resolve(data) == data

    def test_get_corrupt_blob(self, tmp_path: Path):
        store = BlobStore(tmp_path)
        # Write a corrupt blob manually
        sha = "a" * 64
        blob_path = tmp_path / sha[:2] / sha[2:]
        blob_path.parent.mkdir(parents=True)
        blob_path.write_bytes(b"not json{{{")
        with pytest.raises(SchemaError, match="Corrupt blob"):
            store.get(sha)
