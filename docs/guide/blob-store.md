# Blob store

## Overview

Symbolic expressions in computational mathematics can exceed 1 MB in serialized form. The blob store handles large payloads by storing them on disk, referenced by SHA-256 hash.

## How it works

Payloads exceeding 1 MB are stored in a two-level directory structure:

```
.elegua/blobs/
  ab/
    cdef0123...  (SHA-256 hex, first 2 chars as directory)
```

The token stores a reference instead of the full payload:

```json
{"blob": "abcdef0123456789..."}
```

## Usage

```python
from pathlib import Path
from elegua.blobstore import BlobStore

store = BlobStore(root=Path(".elegua/blobs"))
```

### Store and retrieve

```python
ref = store.put({"large_expression": "..." * 1_000_000})
# ref = {"blob": "a1b2c3d4..."}

data = store.get(ref["blob"])
# data == original payload
```

### Transparent handling

Use `maybe_store()` and `maybe_resolve()` for payloads that may or may not exceed the threshold:

```python
# Stores only if > 1 MB, otherwise returns the payload unchanged
result = store.maybe_store(payload)

# Resolves blob refs back to full payloads, passes plain dicts through
data = store.maybe_resolve(result)
```

### Check the threshold

```python
store.should_store(small_payload)  # False
store.should_store(large_payload)  # True
```

## Properties

- **Deterministic** — the same payload always produces the same hash
- **Content-addressed** — duplicate payloads share the same file
- **Two-level directory** — prevents filesystem performance issues with thousands of files
- **Idempotent** — storing the same payload twice is safe
