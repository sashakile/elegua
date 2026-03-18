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
    oracle_tokens = run_tasks(tasks, adapter=adapter)
    iut_tokens = run_tasks(tasks, adapter=adapter)

    # 3. All tasks completed successfully
    assert all(t.status == TaskStatus.OK for t in oracle_tokens)
    assert all(t.status == TaskStatus.OK for t in iut_tokens)

    # 4. Layer 1 identity comparison: Oracle vs IUT
    for oracle, iut in zip(oracle_tokens, iut_tokens):
        status = compare_identity(oracle, iut)
        assert status == TaskStatus.OK, (
            f"Layer 1 comparison failed: {status}"
        )


def test_tracer_bullet_mismatch_detected():
    """Verify the pipeline detects a mismatch when results differ."""
    from elegua.models import ValidationToken

    tasks = load_toml_tasks(FIXTURES / "tracer.toml")
    tokens = run_tasks(tasks)

    tampered = ValidationToken(
        adapter_id="tampered", status=TaskStatus.OK, result={"tampered": True},
    )
    status = compare_identity(tokens[0], tampered)
    assert status == TaskStatus.MATH_MISMATCH
