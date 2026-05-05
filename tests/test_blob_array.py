"""Red-phase tests for NPY array blob manifests, checksums, and lazy reads.

All tests in this file will SKIP until elegua.blob_array is implemented.
See: elegua-06tm, elegua-7ktz.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip(
    "elegua.blob_array",
    reason="elegua.blob_array not yet implemented (elegua-7ktz)",
)

from elegua.blob_array import ArrayManifest, get_array, put_array, validate_manifest
from elegua.blobstore import BlobStore


@pytest.fixture
def store(tmp_path: Path) -> BlobStore:
    return BlobStore(root=tmp_path / "blobs")


# --- Round-trip retrieval ---


class TestArrayBlobRoundTrip:
    def test_float64_round_trip(self, store: BlobStore):
        arr = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        manifest = put_array(store, arr)
        result = get_array(store, manifest)
        np.testing.assert_array_equal(result, arr)

    def test_float32_round_trip(self, store: BlobStore):
        arr = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        manifest = put_array(store, arr)
        result = get_array(store, manifest)
        np.testing.assert_array_equal(result, arr)

    def test_int32_round_trip(self, store: BlobStore):
        arr = np.arange(100, dtype=np.int32)
        manifest = put_array(store, arr)
        result = get_array(store, manifest)
        np.testing.assert_array_equal(result, arr)

    def test_complex128_round_trip(self, store: BlobStore):
        arr = np.array([1 + 2j, 3 + 4j], dtype=np.complex128)
        manifest = put_array(store, arr)
        result = get_array(store, manifest)
        np.testing.assert_array_equal(result, arr)

    def test_multidimensional_round_trip(self, store: BlobStore):
        arr = np.arange(24, dtype=np.float64).reshape(2, 3, 4)
        manifest = put_array(store, arr)
        result = get_array(store, manifest)
        np.testing.assert_array_equal(result, arr)
        assert result.shape == (2, 3, 4)

    def test_large_array_round_trip(self, store: BlobStore):
        rng = np.random.default_rng(0)
        arr = rng.standard_normal(200_000).astype(np.float64)  # ≥1.6 MB to exercise blob path
        manifest = put_array(store, arr)
        result = get_array(store, manifest)
        np.testing.assert_array_equal(result, arr)

    def test_scalar_array_round_trip(self, store: BlobStore):
        arr = np.array(42.0, dtype=np.float64)
        manifest = put_array(store, arr)
        result = get_array(store, manifest)
        np.testing.assert_array_equal(result, arr)

    def test_empty_array_round_trip(self, store: BlobStore):
        arr = np.array([], dtype=np.float64)
        manifest = put_array(store, arr)
        result = get_array(store, manifest)
        assert result.shape == (0,)
        assert result.dtype == np.float64

    def test_dtype_preserved_exactly(self, store: BlobStore):
        arr = np.array([1.0], dtype=np.float32)
        manifest = put_array(store, arr)
        result = get_array(store, manifest)
        assert result.dtype == np.float32

    def test_get_array_missing_blob_raises(self, store: BlobStore):
        arr = np.array([1.0], dtype=np.float64)
        manifest = put_array(store, arr)
        store._blob_path(manifest.sha256).unlink()
        with pytest.raises((FileNotFoundError, KeyError, OSError)):
            get_array(store, manifest)


# --- Manifest structure ---


class TestArrayManifest:
    def test_manifest_schema_version_is_int(self, store: BlobStore):
        arr = np.array([1.0, 2.0], dtype=np.float64)
        manifest = put_array(store, arr)
        assert isinstance(manifest.schema_version, int)
        assert manifest.schema_version >= 1

    def test_manifest_kind_is_npy(self, store: BlobStore):
        arr = np.array([1.0], dtype=np.float64)
        manifest = put_array(store, arr)
        assert manifest.kind == "npy"

    def test_manifest_dtype_matches_array(self, store: BlobStore):
        arr = np.array([1.0, 2.0], dtype=np.float32)
        manifest = put_array(store, arr)
        assert manifest.dtype == "float32"

    def test_manifest_shape_matches_array(self, store: BlobStore):
        arr = np.zeros((3, 4), dtype=np.float64)
        manifest = put_array(store, arr)
        assert manifest.shape == (3, 4)

    def test_manifest_shape_1d(self, store: BlobStore):
        arr = np.zeros(10, dtype=np.float64)
        manifest = put_array(store, arr)
        assert manifest.shape == (10,)

    def test_manifest_compressed_is_bool(self, store: BlobStore):
        arr = np.array([1.0], dtype=np.float64)
        manifest = put_array(store, arr)
        assert isinstance(manifest.compressed, bool)

    def test_manifest_sha256_is_hex_string(self, store: BlobStore):
        arr = np.array([1.0], dtype=np.float64)
        manifest = put_array(store, arr)
        assert isinstance(manifest.sha256, str)
        assert len(manifest.sha256) == 64
        int(manifest.sha256, 16)  # raises ValueError if not valid hex

    def test_manifest_sha256_is_deterministic(self, store: BlobStore):
        arr = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        m1 = put_array(store, arr)
        m2 = put_array(store, arr)
        assert m1.sha256 == m2.sha256

    def test_manifest_sha256_differs_for_different_arrays(self, store: BlobStore):
        a = np.array([1.0], dtype=np.float64)
        b = np.array([2.0], dtype=np.float64)
        m1 = put_array(store, a)
        m2 = put_array(store, b)
        assert m1.sha256 != m2.sha256

    def test_manifest_is_arraymanifest_instance(self, store: BlobStore):
        arr = np.array([1.0], dtype=np.float64)
        manifest = put_array(store, arr)
        assert isinstance(manifest, ArrayManifest)

    def test_compressed_flag_false_by_default(self, store: BlobStore):
        arr = np.array([1.0], dtype=np.float64)
        manifest = put_array(store, arr)
        assert manifest.compressed is False

    def test_compressed_flag_true_when_requested(self, store: BlobStore):
        arr = np.array([1.0], dtype=np.float64)
        manifest = put_array(store, arr, compress=True)
        assert manifest.compressed is True

    def test_compressed_round_trip(self, store: BlobStore):
        arr = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        manifest = put_array(store, arr, compress=True)
        result = get_array(store, manifest)
        np.testing.assert_array_equal(result, arr)


# --- Lazy manifest validation ---


class TestLazyManifestValidation:
    def test_validate_manifest_returns_true_for_valid_blob(self, store: BlobStore):
        arr = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        manifest = put_array(store, arr)
        assert validate_manifest(store, manifest) is True

    def test_validate_manifest_returns_false_for_missing_blob(self, store: BlobStore):
        arr = np.array([1.0], dtype=np.float64)
        manifest = put_array(store, arr)
        # Corrupt the store by removing the blob
        blob_path = store._blob_path(manifest.sha256)
        blob_path.unlink()
        assert validate_manifest(store, manifest) is False

    def test_validate_manifest_does_not_load_full_payload(self, store: BlobStore, monkeypatch):
        arr = np.zeros(1000, dtype=np.float64)
        manifest = put_array(store, arr)

        get_call_count = 0

        original_get = store.get

        def tracking_get(sha: str):
            nonlocal get_call_count
            get_call_count += 1
            return original_get(sha)

        monkeypatch.setattr(store, "get", tracking_get)

        validate_manifest(store, manifest)

        # validate_manifest must check existence via store._blob_path(manifest.sha256).exists(),
        # not by loading the payload through store.get.
        assert get_call_count == 0, "validate_manifest must not load the full blob payload"

    def test_validate_manifest_returns_false_for_unknown_sha256(self, store: BlobStore):
        arr = np.array([1.0, 2.0], dtype=np.float64)
        manifest = put_array(store, arr)

        tampered = ArrayManifest(
            schema_version=manifest.schema_version,
            kind=manifest.kind,
            dtype=manifest.dtype,
            shape=manifest.shape,
            compressed=manifest.compressed,
            sha256="a" * 64,
        )
        assert validate_manifest(store, tampered) is False

    def test_validate_manifest_returns_false_for_corrupted_blob(self, store: BlobStore):
        arr = np.array([1.0, 2.0], dtype=np.float64)
        manifest = put_array(store, arr)
        blob_path = store._blob_path(manifest.sha256)
        blob_path.write_bytes(b"\x00" * len(blob_path.read_bytes()))
        assert validate_manifest(store, manifest) is False

    def test_validate_manifest_returns_false_for_shape_mismatch(self, store: BlobStore):
        arr = np.zeros((3, 4), dtype=np.float64)
        manifest = put_array(store, arr)
        wrong_shape = ArrayManifest(
            schema_version=manifest.schema_version,
            kind=manifest.kind,
            dtype=manifest.dtype,
            shape=(4, 3),
            compressed=manifest.compressed,
            sha256=manifest.sha256,
        )
        assert validate_manifest(store, wrong_shape) is False
