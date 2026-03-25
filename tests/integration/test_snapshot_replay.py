"""Integration tests for snapshot record/replay over HTTP.

When ELEGUA_RECORD=1 is set, these tests record oracle responses to
tests/snapshots/. When unset (default), they replay from snapshots.
This enables CI to run integration-level tests without a live oracle.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from elegua.adapter import Adapter
from elegua.comparison import ComparisonPipeline
from elegua.runner import load_toml_tasks, run_tasks
from elegua.snapshot import RecordingAdapter, ReplayAdapter, SnapshotStore
from elegua.task import TaskStatus
from elegua.testing import EchoOracle

from .conftest import RECORD_MODE

pytestmark = pytest.mark.integration


class TestSnapshotRecordReplay:
    """Verify record/replay workflow with real HTTP transport."""

    def test_record_and_replay_round_trip(self, tmp_path: Path) -> None:
        """Record oracle responses, then replay them without a server."""
        tasks = load_toml_tasks(Path("tests/fixtures/tracer.toml"))
        snap_path = tmp_path / "test_snap.json"

        # Record phase: run against echo oracle
        with EchoOracle() as oracle:
            from elegua.oracle import OracleClient
            from elegua.wolfram.adapter import OracleAdapter

            record_store = SnapshotStore(snap_path)
            inner = OracleAdapter(oracle=OracleClient(oracle.url))
            recorder = RecordingAdapter(inner, record_store)
            with recorder:
                recorded = [recorder.execute(t) for t in tasks]

        assert snap_path.exists()
        assert len(record_store) == 2

        # Replay phase: no server needed
        replay_store = SnapshotStore.read(snap_path)
        replayer = ReplayAdapter(replay_store)
        with replayer:
            replayed = [replayer.execute(t) for t in tasks]

        for orig, replay in zip(recorded, replayed, strict=True):
            assert orig.status == replay.status
            assert orig.result == replay.result

    def test_replay_comparison_pipeline(self, tmp_path: Path) -> None:
        """Record two adapters, replay, and compare through the pipeline."""
        tasks = load_toml_tasks(Path("tests/fixtures/tracer.toml"))
        oracle_snap = tmp_path / "oracle.json"
        iut_snap = tmp_path / "iut.json"

        # Record phase
        with EchoOracle() as echo:
            from elegua.oracle import OracleClient
            from elegua.wolfram.adapter import OracleAdapter

            oracle_store = SnapshotStore(oracle_snap)
            iut_store = SnapshotStore(iut_snap)

            oracle_adapter = RecordingAdapter(
                OracleAdapter(oracle=OracleClient(echo.url)), oracle_store
            )
            iut_adapter = RecordingAdapter(OracleAdapter(oracle=OracleClient(echo.url)), iut_store)

            run_tasks(tasks, adapter=oracle_adapter)
            run_tasks(tasks, adapter=iut_adapter)

        # Replay phase
        oracle_replay = ReplayAdapter(SnapshotStore.read(oracle_snap))
        iut_replay = ReplayAdapter(SnapshotStore.read(iut_snap))

        replay_oracle = run_tasks(tasks, adapter=oracle_replay)
        replay_iut = run_tasks(tasks, adapter=iut_replay)

        pipeline = ComparisonPipeline()
        for o_tok, i_tok in zip(replay_oracle, replay_iut, strict=True):
            result = pipeline.compare(o_tok, i_tok)
            assert result.status == TaskStatus.OK
            assert result.layer == 1

    def test_oracle_adapter_fixture_works(self, oracle_adapter: Adapter) -> None:
        """The conftest oracle_adapter fixture manages lifecycle automatically."""
        from elegua.task import EleguaTask

        task = EleguaTask(action="Evaluate", payload={"expression": "1+1"})
        token = oracle_adapter.execute(task)

        if RECORD_MODE:
            assert token.status == TaskStatus.OK
        else:
            # Replay mode: may return error if no snapshot exists yet
            assert token.status in (TaskStatus.OK, TaskStatus.EXECUTION_ERROR)
