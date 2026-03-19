"""Tests for MultiTierRunner — Oracle vs IUT cross-comparison."""

from __future__ import annotations

from pathlib import Path

import pytest

from elegua.adapter import Adapter
from elegua.bridge import load_sxact_toml
from elegua.comparison import ComparisonPipeline
from elegua.models import ValidationToken
from elegua.multitier import MultiTierRunner, VerificationResult
from elegua.task import EleguaTask, TaskStatus

FIXTURES = Path(__file__).parent / "fixtures"


# --- Helpers ---


class EchoAdapter(Adapter):
    """Returns payload as result (same as WolframAdapter stub)."""

    def __init__(self, name: str = "echo") -> None:
        self._name = name

    @property
    def adapter_id(self) -> str:
        return self._name

    def execute(self, task: EleguaTask) -> ValidationToken:
        return ValidationToken(
            adapter_id=self.adapter_id,
            status=TaskStatus.OK,
            result=task.payload,
        )


class OffsetAdapter(Adapter):
    """Returns payload with an extra key — simulates a different implementation."""

    @property
    def adapter_id(self) -> str:
        return "offset"

    def execute(self, task: EleguaTask) -> ValidationToken:
        result = dict(task.payload)
        result["_offset"] = True
        return ValidationToken(
            adapter_id=self.adapter_id,
            status=TaskStatus.OK,
            result=result,
        )


class FailingAdapter(Adapter):
    """Always returns an execution error."""

    @property
    def adapter_id(self) -> str:
        return "failing"

    def execute(self, task: EleguaTask) -> ValidationToken:
        raise RuntimeError("IUT crashed")


# --- Basic verification ---


def test_verify_matching_adapters():
    """Two identical adapters → all tests pass."""
    runner = MultiTierRunner(
        oracle=EchoAdapter("oracle"),
        iut=EchoAdapter("iut"),
    )
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    with runner:
        results = runner.verify(tf)
    assert len(results) == 2
    assert all(isinstance(r, VerificationResult) for r in results)
    assert all(r.comparison.status == TaskStatus.OK for r in results)


def test_verify_returns_test_ids():
    runner = MultiTierRunner(
        oracle=EchoAdapter("oracle"),
        iut=EchoAdapter("iut"),
    )
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    with runner:
        results = runner.verify(tf)
    assert results[0].test_id == "canon_symmetric"
    assert results[1].test_id == "registry_check"


def test_verify_includes_both_tokens():
    runner = MultiTierRunner(
        oracle=EchoAdapter("oracle"),
        iut=EchoAdapter("iut"),
    )
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    with runner:
        results = runner.verify(tf)
    r = results[0]
    assert r.oracle_token is not None
    assert r.iut_token is not None
    assert r.oracle_token.adapter_id == "oracle"
    assert r.iut_token.adapter_id == "iut"


# --- Mismatch detection ---


def test_verify_detects_mismatch():
    """Different adapters → comparison detects mismatch."""
    runner = MultiTierRunner(
        oracle=EchoAdapter("oracle"),
        iut=OffsetAdapter(),
    )
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    with runner:
        results = runner.verify(tf)
    assert any(r.comparison.status == TaskStatus.MATH_MISMATCH for r in results)


# --- IUT error handling ---


def test_verify_iut_error():
    """IUT crash → EXECUTION_ERROR, not an exception."""
    runner = MultiTierRunner(
        oracle=EchoAdapter("oracle"),
        iut=FailingAdapter(),
    )
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    with runner:
        results = runner.verify(tf)
    # Should have results (not crash)
    assert len(results) == 2
    for r in results:
        assert r.iut_error is not None


# --- Custom pipeline ---


def test_verify_with_custom_pipeline():
    """Custom pipeline layers are used for comparison."""
    always_ok = ComparisonPipeline(default_layers=False)
    always_ok.register(1, "always_ok", lambda a, b: TaskStatus.OK)

    runner = MultiTierRunner(
        oracle=EchoAdapter("oracle"),
        iut=OffsetAdapter(),
        pipeline=always_ok,
    )
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    with runner:
        results = runner.verify(tf)
    assert all(r.comparison.status == TaskStatus.OK for r in results)


# --- Context manager ---


def test_must_use_context_manager():
    runner = MultiTierRunner(
        oracle=EchoAdapter("oracle"),
        iut=EchoAdapter("iut"),
    )
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    with pytest.raises(RuntimeError, match="context manager"):
        runner.verify(tf)


# --- Empty test file ---


def test_verify_empty_file(tmp_path: Path):
    f = tmp_path / "empty.toml"
    f.write_text('[meta]\nid = "e"\ndescription = "d"\n')
    tf = load_sxact_toml(f)
    runner = MultiTierRunner(
        oracle=EchoAdapter("oracle"),
        iut=EchoAdapter("iut"),
    )
    with runner:
        results = runner.verify(tf)
    assert results == []


# --- Skipped tests ---


def test_verify_skipped_test(tmp_path: Path):
    f = tmp_path / "t.toml"
    f.write_text(
        '[meta]\nid = "t"\ndescription = "d"\n\n'
        '[[tests]]\nid = "t1"\ndescription = "d"\nskip = "not ready"\n\n'
        '[[tests.operations]]\naction = "Foo"\n'
    )
    tf = load_sxact_toml(f)
    runner = MultiTierRunner(
        oracle=EchoAdapter("oracle"),
        iut=EchoAdapter("iut"),
    )
    with runner:
        results = runner.verify(tf)
    assert results[0].skipped is True
