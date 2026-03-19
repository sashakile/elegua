"""Tests for IsolatedRunner — per-file lifecycle and per-test binding scope."""

from __future__ import annotations

from pathlib import Path

import pytest

from elegua.adapter import Adapter, WolframAdapter
from elegua.bridge import load_sxact_toml
from elegua.isolation import IsolatedRunner, TestRunResult
from elegua.models import ValidationToken
from elegua.task import EleguaTask, TaskStatus

FIXTURES = Path(__file__).parent / "fixtures"


# --- Basic lifecycle ---


def test_run_returns_results_per_test():
    runner = IsolatedRunner(WolframAdapter())
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    with runner:
        results = runner.run(tf)
    assert len(results) == 2
    assert all(isinstance(r, TestRunResult) for r in results)


def test_result_has_test_id():
    runner = IsolatedRunner(WolframAdapter())
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    with runner:
        results = runner.run(tf)
    assert results[0].test_id == "canon_symmetric"
    assert results[1].test_id == "registry_check"


def test_result_has_tokens_per_operation():
    runner = IsolatedRunner(WolframAdapter())
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    with runner:
        results = runner.run(tf)
    # canon_symmetric has 3 operations
    assert len(results[0].tokens) == 3
    # registry_check has 1 operation
    assert len(results[1].tokens) == 1


def test_all_tokens_are_ok():
    runner = IsolatedRunner(WolframAdapter())
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    with runner:
        results = runner.run(tf)
    for r in results:
        assert all(t.status == TaskStatus.OK for t in r.tokens)


# --- Adapter lifecycle ---


def test_adapter_lifecycle_called():
    class TrackingAdapter(Adapter):
        def __init__(self):
            self.calls: list[str] = []

        @property
        def adapter_id(self) -> str:
            return "tracking"

        def initialize(self) -> None:
            self.calls.append("initialize")

        def teardown(self) -> None:
            self.calls.append("teardown")

        def execute(self, task: EleguaTask) -> ValidationToken:
            self.calls.append(f"execute:{task.action}")
            return ValidationToken(
                adapter_id=self.adapter_id,
                status=TaskStatus.OK,
                result=task.payload,
            )

    adapter = TrackingAdapter()
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    with IsolatedRunner(adapter) as runner:
        runner.run(tf)

    assert adapter.calls[0] == "initialize"
    assert adapter.calls[-1] == "teardown"


# --- Binding isolation ---


def test_setup_bindings_visible_in_tests(tmp_path: Path):
    """Setup store_as bindings are available in all tests."""
    f = tmp_path / "t.toml"
    f.write_text(
        '[meta]\nid = "t"\ndescription = "d"\n\n'
        '[[setup]]\naction = "Set"\nstore_as = "X"\n'
        '[setup.args]\nvalue = "hello"\n\n'
        '[[tests]]\nid = "t1"\ndescription = "d"\n\n'
        '[[tests.operations]]\naction = "Read"\n'
        '[tests.operations.args]\nexpr = "$X"\n'
    )
    tf = load_sxact_toml(f)
    runner = IsolatedRunner(WolframAdapter())
    with runner:
        results = runner.run(tf)
    # The stub adapter echoes the payload, so the resolved $X should appear
    token = results[0].tokens[0]
    assert token.result is not None
    # $X was resolved to the string repr of the stored result
    assert token.result["expr"] != "$X"


def test_store_as_extracts_repr_from_dict(tmp_path: Path):
    """When result is a dict with 'repr', store_as uses the repr string."""

    class ReprAdapter(Adapter):
        """Setup ops return dict with repr key. Test ops echo payload."""

        @property
        def adapter_id(self) -> str:
            return "repr"

        def execute(self, task: EleguaTask) -> ValidationToken:
            if task.action == "Eval":
                return ValidationToken(
                    adapter_id=self.adapter_id,
                    status=TaskStatus.OK,
                    result={"repr": "T[-a,-b]", "type": "Expr"},
                )
            # Echo payload so we can see what $expr1 resolved to
            return ValidationToken(
                adapter_id=self.adapter_id,
                status=TaskStatus.OK,
                result=task.payload,
            )

    f = tmp_path / "t.toml"
    f.write_text(
        '[meta]\nid = "t"\ndescription = "d"\n\n'
        '[[setup]]\naction = "Eval"\nstore_as = "expr1"\n\n'
        '[[tests]]\nid = "t1"\ndescription = "d"\n\n'
        '[[tests.operations]]\naction = "Read"\n'
        '[tests.operations.args]\ninput = "$expr1"\n'
    )
    tf = load_sxact_toml(f)
    runner = IsolatedRunner(ReprAdapter())
    with runner:
        results = runner.run(tf)
    token = results[0].tokens[0]
    assert token.result is not None
    # $expr1 should resolve to the repr string, not the full dict
    assert token.result["input"] == "T[-a,-b]"


def test_test_bindings_do_not_leak(tmp_path: Path):
    """Bindings from test 1 are not visible in test 2."""
    f = tmp_path / "t.toml"
    f.write_text(
        '[meta]\nid = "t"\ndescription = "d"\n\n'
        '[[tests]]\nid = "t1"\ndescription = "d"\n\n'
        '[[tests.operations]]\naction = "Eval"\nstore_as = "local_var"\n'
        '[tests.operations.args]\nvalue = "secret"\n\n'
        '[[tests]]\nid = "t2"\ndescription = "d"\n\n'
        '[[tests.operations]]\naction = "Read"\n'
        '[tests.operations.args]\nexpr = "$local_var"\n'
    )
    tf = load_sxact_toml(f)
    runner = IsolatedRunner(WolframAdapter())
    with runner:
        results = runner.run(tf)
    # t2 should see $local_var unresolved (leaked binding = bug)
    token = results[1].tokens[0]
    assert token.result is not None
    assert token.result["expr"] == "$local_var"


# --- Skip handling ---


def test_skipped_test(tmp_path: Path):
    f = tmp_path / "t.toml"
    f.write_text(
        '[meta]\nid = "t"\ndescription = "d"\n\n'
        '[[tests]]\nid = "t1"\ndescription = "d"\nskip = "not ready"\n\n'
        '[[tests.operations]]\naction = "Foo"\n'
    )
    tf = load_sxact_toml(f)
    runner = IsolatedRunner(WolframAdapter())
    with runner:
        results = runner.run(tf)
    assert results[0].skipped is True
    assert results[0].skip_reason == "not ready"
    assert results[0].tokens == []


# --- Error handling ---


def test_execution_error_captured():
    class FailAdapter(Adapter):
        @property
        def adapter_id(self) -> str:
            return "fail"

        def execute(self, task: EleguaTask) -> ValidationToken:
            raise RuntimeError("kernel crashed")

    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    runner = IsolatedRunner(FailAdapter())
    with runner:
        results = runner.run(tf)
    # Setup fails, so tests should have errors
    assert results[0].error is not None


# --- Must be used as context manager ---


def test_run_outside_context_raises():
    runner = IsolatedRunner(WolframAdapter())
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    with pytest.raises(RuntimeError, match="must be used as a context manager"):
        runner.run(tf)


# --- Empty test file ---


def test_empty_test_file(tmp_path: Path):
    f = tmp_path / "empty.toml"
    f.write_text('[meta]\nid = "e"\ndescription = "d"\n')
    tf = load_sxact_toml(f)
    runner = IsolatedRunner(WolframAdapter())
    with runner:
        results = runner.run(tf)
    assert results == []
