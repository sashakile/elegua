"""Shared fixtures for integration tests.

Snapshot record/replay mode:
    ELEGUA_RECORD=1 just test-integration   → records oracle responses to tests/snapshots/
    just test-integration                    → replays from snapshots (default)
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from elegua.oracle import OracleClient
from elegua.snapshot import RecordingAdapter, ReplayAdapter, SnapshotStore
from elegua.testing import EchoOracle
from elegua.wolfram.adapter import WolframOracleAdapter

SNAPSHOT_DIR = Path("tests/snapshots")
RECORD_MODE = os.environ.get("ELEGUA_RECORD", "") == "1"


@pytest.fixture(scope="module")
def echo_oracle():
    """Module-scoped echo oracle server."""
    with EchoOracle() as oracle:
        yield oracle


@pytest.fixture(scope="module")
def snapshot_store(request: pytest.FixtureRequest) -> SnapshotStore:
    """Snapshot store scoped to the test module.

    In record mode, writes to ``tests/snapshots/<module>.json``.
    In replay mode, reads from the same path.
    Module-scoped so recordings accumulate across tests.
    """
    module_name = request.module.__name__.rsplit(".", 1)[-1]
    path = SNAPSHOT_DIR / f"{module_name}.json"
    return SnapshotStore.read(path)


@pytest.fixture()
def oracle_adapter(echo_oracle, snapshot_store):  # type: ignore[no-untyped-def]
    """Adapter that records or replays depending on ELEGUA_RECORD.

    Record mode (ELEGUA_RECORD=1): wraps a real adapter and captures results.
    Replay mode (default): serves cached results from snapshots.

    Lifecycle is managed here so tests don't need a context manager.
    """
    if RECORD_MODE:
        inner = WolframOracleAdapter(oracle=OracleClient(echo_oracle.url))
        adapter = RecordingAdapter(inner, snapshot_store)
    else:
        adapter = ReplayAdapter(snapshot_store)
    adapter.initialize()
    yield adapter
    adapter.teardown()
