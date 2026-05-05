"""NPY array blob storage: put/get arrays via BlobStore with SHA-256 manifests."""

from __future__ import annotations

import gzip
import hashlib
import io
from dataclasses import dataclass

import numpy as np

from elegua.blobstore import BlobStore

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ArrayManifest:
    schema_version: int
    kind: str
    dtype: str
    shape: tuple[int, ...]
    compressed: bool
    sha256: str


def put_array(store: BlobStore, arr: np.ndarray, compress: bool = False) -> ArrayManifest:
    buf = io.BytesIO()
    np.save(buf, arr, allow_pickle=False)
    data = buf.getvalue()

    if compress:
        data = gzip.compress(data)

    sha = hashlib.sha256(data).hexdigest()
    blob_path = store._blob_path(sha)
    blob_path.parent.mkdir(parents=True, exist_ok=True)
    blob_path.write_bytes(data)

    return ArrayManifest(
        schema_version=SCHEMA_VERSION,
        kind="npy",
        dtype=str(arr.dtype),
        shape=tuple(arr.shape),
        compressed=compress,
        sha256=sha,
    )


def get_array(store: BlobStore, manifest: ArrayManifest) -> np.ndarray:
    blob_path = store._blob_path(manifest.sha256)
    data = blob_path.read_bytes()  # raises FileNotFoundError if missing

    if manifest.compressed:
        data = gzip.decompress(data)

    return np.load(io.BytesIO(data), allow_pickle=False)


def validate_manifest(store: BlobStore, manifest: ArrayManifest) -> bool:
    blob_path = store._blob_path(manifest.sha256)
    if not blob_path.exists():
        return False

    data = blob_path.read_bytes()

    # Verify content integrity without going through store.get (which parses JSON)
    if hashlib.sha256(data).hexdigest() != manifest.sha256:
        return False

    try:
        npy_data = gzip.decompress(data) if manifest.compressed else data
        arr = np.load(io.BytesIO(npy_data), allow_pickle=False)
        return arr.shape == manifest.shape and arr.dtype == np.dtype(manifest.dtype)
    except (ValueError, OSError, gzip.BadGzipFile):
        return False
