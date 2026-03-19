"""Per-file test isolation and lifecycle management.

Orchestrates adapter lifecycle, ExecutionContext scoping, and
test execution for sxAct-format test files.

Usage::

    runner = IsolatedRunner(adapter)
    with runner:
        results = runner.run(test_file)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Self

from elegua.adapter import Adapter
from elegua.bridge import Operation, TestCase, TestFile
from elegua.context import ExecutionContext
from elegua.models import ValidationToken
from elegua.task import EleguaTask


@dataclass(frozen=True)
class TestRunResult:
    """Result of running a single test case."""

    __test__ = False

    test_id: str
    tokens: list[ValidationToken] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None
    error: str | None = None


class IsolatedRunner:
    """Manages adapter lifecycle and binding scope for a TestFile.

    State machine::

        INIT → SETUP → TESTS → TEARDOWN

    Binding scope::

        - Setup store_as  → available to ALL tests in the file
        - Per-test store_as → available only within that test
    """

    def __init__(self, adapter: Adapter) -> None:
        self._adapter = adapter
        self._context = ExecutionContext()
        self._ready = False

    def __enter__(self) -> Self:
        self._adapter.initialize()
        self._ready = True
        return self

    def __exit__(self, *_: object) -> None:
        self._adapter.teardown()
        self._ready = False

    def run(self, test_file: TestFile) -> list[TestRunResult]:
        """Run all tests with setup-first, per-test isolation.

        Raises RuntimeError if called outside a ``with`` block.
        """
        if not self._ready:
            raise RuntimeError("IsolatedRunner must be used as a context manager")

        try:
            self._run_setup(test_file.setup)
        except Exception as exc:
            return [TestRunResult(test_id=tc.id, error=str(exc)) for tc in test_file.tests]

        setup_snap = self._context.snapshot()

        results: list[TestRunResult] = []
        for tc in test_file.tests:
            self._context.restore(setup_snap)
            results.append(self._run_test(tc))
        return results

    def _run_setup(self, setup_ops: list[Operation]) -> None:
        for op in setup_ops:
            self._execute_op(op)

    def _run_test(self, tc: TestCase) -> TestRunResult:
        if tc.skip:
            return TestRunResult(test_id=tc.id, skipped=True, skip_reason=tc.skip)

        tokens: list[ValidationToken] = []
        try:
            for op in tc.operations:
                token = self._execute_op(op)
                tokens.append(token)
        except Exception as exc:
            return TestRunResult(test_id=tc.id, tokens=tokens, error=str(exc))

        return TestRunResult(test_id=tc.id, tokens=tokens)

    def _execute_op(self, op: Operation) -> ValidationToken:
        resolved_args = self._context.resolve_refs(op.args)
        task = EleguaTask(action=op.action, payload=resolved_args)
        token = self._adapter.execute(task)
        if op.store_as is not None and token.result is not None:
            value = (
                token.result.get("repr", str(token.result))
                if isinstance(token.result, dict)
                else str(token.result)
            )
            self._context.store(op.store_as, value)
        return token
