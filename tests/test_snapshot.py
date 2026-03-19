"""Tests for snapshot record/replay infrastructure."""

from __future__ import annotations

from pathlib import Path

import pytest

from elegua.adapter import WolframAdapter
from elegua.errors import SchemaError
from elegua.models import ValidationToken
from elegua.snapshot import RecordingAdapter, ReplayAdapter, SnapshotStore
from elegua.task import EleguaTask, TaskStatus

# --- SnapshotStore ---


def test_store_key_deterministic():
    k1 = SnapshotStore.key("Eval", {"x": 1})
    k2 = SnapshotStore.key("Eval", {"x": 1})
    assert k1 == k2


def test_store_key_differs_by_action():
    k1 = SnapshotStore.key("Eval", {"x": 1})
    k2 = SnapshotStore.key("Simplify", {"x": 1})
    assert k1 != k2


def test_store_key_differs_by_payload():
    k1 = SnapshotStore.key("Eval", {"x": 1})
    k2 = SnapshotStore.key("Eval", {"x": 2})
    assert k1 != k2


def test_store_key_ignores_dict_order():
    k1 = SnapshotStore.key("Eval", {"a": 1, "b": 2})
    k2 = SnapshotStore.key("Eval", {"b": 2, "a": 1})
    assert k1 == k2


def test_store_save_and_load(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snap.json")
    token = ValidationToken(adapter_id="test", status=TaskStatus.OK, result={"repr": "42"})
    store.save("key1", token)
    loaded = store.load("key1")
    assert loaded is not None
    assert loaded.status == TaskStatus.OK
    assert loaded.result == {"repr": "42"}


def test_store_load_missing_returns_none(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snap.json")
    assert store.load("nonexistent") is None


def test_store_write_and_read(tmp_path: Path):
    path = tmp_path / "snap.json"
    store = SnapshotStore(path)
    token = ValidationToken(
        adapter_id="test",
        status=TaskStatus.OK,
        result={"repr": "T[-a,-b]"},
        metadata={"timing_ms": 100},
    )
    store.save("k1", token)
    store.write()

    # Read back from disk
    store2 = SnapshotStore.read(path)
    loaded = store2.load("k1")
    assert loaded is not None
    assert loaded.result == {"repr": "T[-a,-b]"}
    assert loaded.metadata == {"timing_ms": 100}


def test_store_read_nonexistent_returns_empty(tmp_path: Path):
    store = SnapshotStore.read(tmp_path / "missing.json")
    assert store.load("anything") is None


def test_store_count(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snap.json")
    assert len(store) == 0
    store.save("k1", ValidationToken(adapter_id="t", status=TaskStatus.OK))
    store.save("k2", ValidationToken(adapter_id="t", status=TaskStatus.OK))
    assert len(store) == 2


# --- RecordingAdapter ---


def test_recording_adapter_delegates_execute():
    store = SnapshotStore()
    adapter = RecordingAdapter(WolframAdapter(), store)
    task = EleguaTask(action="Eval", payload={"expression": "1+1"})
    with adapter:
        token = adapter.execute(task)
    assert token.status == TaskStatus.OK


def test_recording_adapter_captures_result():
    store = SnapshotStore()
    adapter = RecordingAdapter(WolframAdapter(), store)
    task = EleguaTask(action="Eval", payload={"expression": "1+1"})
    with adapter:
        adapter.execute(task)
    key = SnapshotStore.key("Eval", {"expression": "1+1"})
    assert store.load(key) is not None


def test_recording_adapter_persists_on_teardown(tmp_path: Path):
    path = tmp_path / "snap.json"
    store = SnapshotStore(path)
    adapter = RecordingAdapter(WolframAdapter(), store)
    task = EleguaTask(action="Eval", payload={"expression": "1+1"})
    with adapter:
        adapter.execute(task)
    # After teardown, file should exist
    assert path.exists()


def test_recording_adapter_preserves_adapter_id():
    store = SnapshotStore()
    adapter = RecordingAdapter(WolframAdapter(), store)
    assert adapter.adapter_id == "wolfram"


# --- ReplayAdapter ---


def test_replay_returns_cached_token():
    store = SnapshotStore()
    token = ValidationToken(adapter_id="original", status=TaskStatus.OK, result={"repr": "42"})
    key = SnapshotStore.key("Eval", {"expression": "1+1"})
    store.save(key, token)

    adapter = ReplayAdapter(store)
    task = EleguaTask(action="Eval", payload={"expression": "1+1"})
    with adapter:
        replayed = adapter.execute(task)
    assert replayed.status == TaskStatus.OK
    assert replayed.result == {"repr": "42"}


def test_replay_missing_snapshot_returns_error():
    store = SnapshotStore()
    adapter = ReplayAdapter(store)
    task = EleguaTask(action="Unknown", payload={})
    with adapter:
        token = adapter.execute(task)
    assert token.status == TaskStatus.EXECUTION_ERROR
    assert "No snapshot" in (token.metadata.get("error") or "")


def test_replay_adapter_id():
    adapter = ReplayAdapter(SnapshotStore())
    assert adapter.adapter_id == "replay"


# --- Round-trip: record then replay ---


def test_record_then_replay(tmp_path: Path):
    path = tmp_path / "snap.json"

    # Record phase
    record_store = SnapshotStore(path)
    recorder = RecordingAdapter(WolframAdapter(), record_store)
    tasks = [
        EleguaTask(action="A", payload={"x": 1}),
        EleguaTask(action="B", payload={"y": 2}),
    ]
    with recorder:
        recorded_tokens = [recorder.execute(t) for t in tasks]

    # Replay phase (no oracle)
    replay_store = SnapshotStore.read(path)
    replayer = ReplayAdapter(replay_store)
    with replayer:
        replayed_tokens = [replayer.execute(t) for t in tasks]

    for orig, replayed in zip(recorded_tokens, replayed_tokens, strict=True):
        assert orig.status == replayed.status
        assert orig.result == replayed.result


# --- Corrupt JSON ---


def test_read_corrupt_json(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{truncated")
    with pytest.raises(SchemaError, match="corrupt snapshot JSON"):
        SnapshotStore.read(f)


def test_read_non_dict_json(tmp_path):
    f = tmp_path / "arr.json"
    f.write_text("[1, 2, 3]")
    with pytest.raises(SchemaError, match="expected JSON object"):
        SnapshotStore.read(f)
