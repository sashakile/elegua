"""Tracer bullet: DefTensor+Contract round-trip through entire architecture.

This is THE test. If it passes, the Eleguá architecture works end-to-end:
  TOML fixture → EleguaTask → WolframAdapter → Layer 1 comparison → pass/fail
"""

from __future__ import annotations

from pathlib import Path

from elegua.adapter import WolframAdapter
from elegua.comparison import compare_identity
from elegua.runner import load_toml_tasks, run_tasks
from elegua.task import TaskStatus

FIXTURES = Path(__file__).parent / "fixtures"


def test_tracer_bullet_end_to_end():
    """Full vertical slice: load → execute twice → compare → pass."""
    # 1. Load tasks from TOML
    tasks = load_toml_tasks(FIXTURES / "tracer.toml")
    assert len(tasks) == 2

    # 2. Execute through adapter twice (simulating Oracle vs IUT)
    adapter = WolframAdapter()
    oracle_results = run_tasks(tasks, adapter=adapter)
    iut_results = run_tasks(tasks, adapter=adapter)

    # 3. All tasks completed successfully
    assert all(r.status == TaskStatus.OK for r in oracle_results)
    assert all(r.status == TaskStatus.OK for r in iut_results)

    # 4. Layer 1 identity comparison: Oracle vs IUT
    for oracle, iut in zip(oracle_results, iut_results):
        assert oracle.result is not None
        assert iut.result is not None
        status = compare_identity(oracle.result, iut.result)
        assert status == TaskStatus.OK, (
            f"Layer 1 comparison failed for {oracle.action}: {status}"
        )


def test_tracer_bullet_mismatch_detected():
    """Verify the pipeline detects a mismatch when results differ."""
    tasks = load_toml_tasks(FIXTURES / "tracer.toml")
    results = run_tasks(tasks)

    # Tamper with one result to simulate a mismatch
    tampered = {"tampered": True}
    status = compare_identity(results[0].result, tampered)
    assert status == TaskStatus.MATH_MISMATCH
