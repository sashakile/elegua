"""Multi-tier verification — Oracle vs IUT cross-comparison.

Executes the same TestFile on an oracle adapter and an IUT adapter,
then compares results per test via ComparisonPipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import zip_longest
from typing import Self

from elegua.adapter import Adapter
from elegua.bridge import TestFile
from elegua.comparison import ComparisonPipeline, ComparisonResult
from elegua.isolation import IsolatedRunner, TestRunResult
from elegua.models import ValidationToken
from elegua.task import TaskStatus

_DEFAULT_COMPARISON = ComparisonResult(status=TaskStatus.MATH_MISMATCH, layer=0)


@dataclass(frozen=True)
class VerificationResult:
    """Cross-tier comparison result for a single test."""

    __test__ = False

    test_id: str
    oracle_token: ValidationToken | None = None
    iut_token: ValidationToken | None = None
    comparison: ComparisonResult = field(default=_DEFAULT_COMPARISON)
    oracle_error: str | None = None
    iut_error: str | None = None
    skipped: bool = False
    skip_reason: str | None = None


class MultiTierRunner:
    """Runs a TestFile on oracle + IUT adapters and compares results.

    Each adapter gets its own IsolatedRunner with independent lifecycle
    and binding scope.
    """

    def __init__(
        self,
        oracle: Adapter,
        iut: Adapter,
        pipeline: ComparisonPipeline | None = None,
    ) -> None:
        self._oracle_runner = IsolatedRunner(oracle)
        self._iut_runner = IsolatedRunner(iut)
        self._pipeline = pipeline or ComparisonPipeline()
        self._ready = False

    def __enter__(self) -> Self:
        self._oracle_runner.__enter__()
        try:
            self._iut_runner.__enter__()
        except Exception:
            self._oracle_runner.__exit__(None, None, None)
            raise
        self._ready = True
        return self

    def __exit__(self, *exc: object) -> None:
        self._ready = False
        try:
            self._iut_runner.__exit__(*exc)
        finally:
            self._oracle_runner.__exit__(*exc)

    def verify(self, test_file: TestFile) -> list[VerificationResult]:
        """Run test_file on both tiers, compare last token per test."""
        if not self._ready:
            raise RuntimeError("MultiTierRunner must be used as a context manager")

        oracle_results = self._oracle_runner.run(test_file)
        iut_results = self._iut_runner.run(test_file)

        verifications: list[VerificationResult] = []
        for oracle_r, iut_r in zip_longest(oracle_results, iut_results):
            if oracle_r is None:
                verifications.append(
                    VerificationResult(
                        test_id=iut_r.test_id,
                        iut_token=iut_r.tokens[-1] if iut_r.tokens else None,
                        comparison=ComparisonResult(status=TaskStatus.EXECUTION_ERROR, layer=0),
                        oracle_error="Missing oracle result for this test",
                    )
                )
            elif iut_r is None:
                verifications.append(
                    VerificationResult(
                        test_id=oracle_r.test_id,
                        oracle_token=oracle_r.tokens[-1] if oracle_r.tokens else None,
                        comparison=ComparisonResult(status=TaskStatus.EXECUTION_ERROR, layer=0),
                        iut_error="Missing IUT result for this test",
                    )
                )
            else:
                verifications.append(self._compare_test(oracle_r, iut_r))
        return verifications

    def _compare_test(self, oracle_r: TestRunResult, iut_r: TestRunResult) -> VerificationResult:
        # Skipped tests
        if oracle_r.skipped or iut_r.skipped:
            return VerificationResult(
                test_id=oracle_r.test_id,
                skipped=True,
                skip_reason=oracle_r.skip_reason or iut_r.skip_reason,
            )

        # Extract last token from each side
        oracle_token = oracle_r.tokens[-1] if oracle_r.tokens else None
        iut_token = iut_r.tokens[-1] if iut_r.tokens else None

        # If either side errored during execution
        if oracle_r.error or iut_r.error:
            return VerificationResult(
                test_id=oracle_r.test_id,
                oracle_token=oracle_token,
                iut_token=iut_token,
                comparison=ComparisonResult(status=TaskStatus.EXECUTION_ERROR, layer=0),
                oracle_error=oracle_r.error,
                iut_error=iut_r.error,
            )

        # If either side has no token
        if oracle_token is None or iut_token is None:
            return VerificationResult(
                test_id=oracle_r.test_id,
                oracle_token=oracle_token,
                iut_token=iut_token,
                comparison=ComparisonResult(status=TaskStatus.EXECUTION_ERROR, layer=0),
            )

        # Compare via pipeline
        comparison = self._pipeline.compare(oracle_token, iut_token)
        return VerificationResult(
            test_id=oracle_r.test_id,
            oracle_token=oracle_token,
            iut_token=iut_token,
            comparison=comparison,
        )
