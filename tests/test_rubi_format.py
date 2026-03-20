"""RUBI format validation — TOML → load → IsolatedRunner → verdict with echo adapter.

Proves the existing pipeline handles non-tensor (integration rule) domains
without code changes. Uses the integrate-then-differentiate pattern with
store_as + dollar-ref chaining.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from elegua.adapter import Adapter
from elegua.bridge import TestFile, load_test_file
from elegua.isolation import IsolatedRunner
from elegua.models import ValidationToken
from elegua.task import EleguaTask, TaskStatus
from elegua.verdict import evaluate_expected

FIXTURES = Path(__file__).parent / "fixtures"
RUBI_FILES = sorted(FIXTURES.glob("rubi_*.toml"))


class CASEchoAdapter(Adapter):
    """Echoes the 'expression' arg as repr — simulates a CAS round-trip.

    For any action (Integrate, Differentiate, etc.), returns the expression
    argument as the repr in the result. This lets store_as + $ref chaining
    produce the expected round-trip values.
    """

    @property
    def adapter_id(self) -> str:
        return "cas-echo"

    def execute(self, task: EleguaTask) -> ValidationToken:
        expr = task.payload.get("expression", "")
        return ValidationToken(
            adapter_id=self.adapter_id,
            status=TaskStatus.OK,
            result={"repr": expr},
        )


# --- TOML loading ---


@pytest.mark.parametrize("toml_path", RUBI_FILES, ids=lambda p: p.stem)
def test_rubi_toml_loads(toml_path: Path):
    """Each RUBI TOML file parses into a valid TestFile."""
    tf = load_test_file(toml_path)
    assert isinstance(tf, TestFile)
    assert tf.meta.id.startswith("rubi/")
    assert "rubi" in tf.meta.tags
    assert len(tf.tests) >= 1


@pytest.mark.parametrize("toml_path", RUBI_FILES, ids=lambda p: p.stem)
def test_rubi_toml_has_integrate_differentiate_pattern(toml_path: Path):
    """Each RUBI test uses the Integrate → store → Differentiate → check pattern."""
    tf = load_test_file(toml_path)
    for tc in tf.tests:
        actions = [op.action for op in tc.operations]
        assert "Integrate" in actions, f"{tc.id}: missing Integrate action"
        assert "Differentiate" in actions, f"{tc.id}: missing Differentiate action"
        # Integrate must come before Differentiate
        assert actions.index("Integrate") < actions.index("Differentiate")
        # Integrate must have store_as
        integrate_op = next(op for op in tc.operations if op.action == "Integrate")
        assert integrate_op.store_as is not None, f"{tc.id}: Integrate needs store_as"
        # Differentiate must reference the stored value
        diff_op = next(op for op in tc.operations if op.action == "Differentiate")
        assert "$" in diff_op.args.get("expression", ""), (
            f"{tc.id}: Differentiate should use $ref to stored antiderivative"
        )


# --- Pipeline execution ---


@pytest.mark.parametrize("toml_path", RUBI_FILES, ids=lambda p: p.stem)
def test_rubi_pipeline_execution(toml_path: Path):
    """RUBI files run through IsolatedRunner without errors."""
    tf = load_test_file(toml_path)
    adapter = CASEchoAdapter()
    runner = IsolatedRunner(adapter)
    with runner:
        results = runner.run(tf)

    assert len(results) == len(tf.tests)
    for r in results:
        assert r.error is None, f"{r.test_id}: unexpected error: {r.error}"
        assert len(r.tokens) >= 2, (
            f"{r.test_id}: expected at least 2 tokens (Integrate + Differentiate)"
        )


# --- Verdict evaluation ---


@pytest.mark.parametrize("toml_path", RUBI_FILES, ids=lambda p: p.stem)
def test_rubi_verdict_passes(toml_path: Path):
    """CAS echo adapter produces correct round-trip → verdict passes."""
    tf = load_test_file(toml_path)
    adapter = CASEchoAdapter()
    runner = IsolatedRunner(adapter)
    with runner:
        results = runner.run(tf)

    for result, tc in zip(results, tf.tests, strict=True):
        verdict = evaluate_expected(result, tc)
        assert verdict.status == "pass", f"{tc.id}: verdict {verdict.status}: {verdict.message}"


# --- Structural checks ---


def test_at_least_three_rubi_files():
    """Acceptance criterion: at least 3 RUBI rule files."""
    assert len(RUBI_FILES) >= 3, f"Expected >= 3 RUBI files, found {len(RUBI_FILES)}"


def test_rubi_files_cover_different_rules():
    """Each RUBI file tests a distinct integration rule."""
    ids = set()
    for toml_path in RUBI_FILES:
        tf = load_test_file(toml_path)
        ids.add(tf.meta.id)
    assert len(ids) >= 3, f"Expected >= 3 distinct rules, found {ids}"
