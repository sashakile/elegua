"""Integration tests exercising the full pipeline over HTTP via the echo oracle.

These tests prove the HTTP transport and adapter lifecycle work end-to-end
without requiring a real Wolfram kernel. The echo oracle echoes expressions
back as results, so identity-layer comparisons always pass.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from elegua.comparison import ComparisonPipeline
from elegua.oracle import OracleClient
from elegua.runner import load_toml_tasks, run_tasks
from elegua.task import TaskStatus
from elegua.testing import EchoOracle
from elegua.wolfram.adapter import WolframOracleAdapter

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def echo_oracle():
    """Module-scoped echo oracle server."""
    with EchoOracle() as oracle:
        yield oracle


@pytest.fixture()
def client(echo_oracle):
    """OracleClient pointed at the echo oracle."""
    return OracleClient(echo_oracle.url)


@pytest.fixture()
def adapter(echo_oracle):
    """WolframOracleAdapter using the echo oracle."""
    return WolframOracleAdapter(
        oracle=OracleClient(echo_oracle.url),
    )


# --- OracleClient over HTTP ---


class TestOracleClientHTTP:
    """Verify OracleClient works against a real HTTP server."""

    def test_health_returns_true(self, client: OracleClient) -> None:
        assert client.health() is True

    def test_health_or_raise_succeeds(self, client: OracleClient) -> None:
        client.health_or_raise()

    def test_evaluate_with_xact_echoes_expression(self, client: OracleClient) -> None:
        result = client.evaluate_with_xact("1 + 1", timeout=5)
        assert result["status"] == "ok"
        assert result["result"] == "1 + 1"

    def test_evaluate_with_context_id(self, client: OracleClient) -> None:
        result = client.evaluate_with_xact("x", timeout=5, context_id="test-ctx")
        assert result["status"] == "ok"

    def test_cleanup_returns_true(self, client: OracleClient) -> None:
        assert client.cleanup() is True

    def test_check_clean_state(self, client: OracleClient) -> None:
        is_clean, leaked = client.check_clean_state()
        assert is_clean is True
        assert leaked == []


# --- Adapter lifecycle over HTTP ---


class TestAdapterLifecycleHTTP:
    """Verify adapter initialize/teardown work over real HTTP."""

    def test_context_manager_lifecycle(self, adapter: WolframOracleAdapter) -> None:
        with adapter:
            task = load_toml_tasks(Path("tests/fixtures/tracer.toml"))[0]
            token = adapter.execute(task)
            assert token.status == TaskStatus.OK
            assert token.adapter_id == "wolfram-oracle"

    def test_execute_echoes_expression(self, adapter: WolframOracleAdapter) -> None:
        from elegua.task import EleguaTask

        with adapter:
            task = EleguaTask(action="Evaluate", payload={"expression": "T[-a,-b]"})
            token = adapter.execute(task)
            assert token.status == TaskStatus.OK
            assert token.result is not None
            assert token.result["repr"] == "T[-a,-b]"


# --- Full pipeline over HTTP ---


class TestPipelineHTTP:
    """Verify the comparison pipeline works end-to-end over HTTP."""

    def test_load_and_compare_tracer_fixture(self, echo_oracle) -> None:  # type: ignore[no-untyped-def]
        """Load tracer fixture, run through two adapters, compare results."""
        tasks = load_toml_tasks(Path("tests/fixtures/tracer.toml"))

        oracle_adapter = WolframOracleAdapter(oracle=OracleClient(echo_oracle.url))
        iut_adapter = WolframOracleAdapter(oracle=OracleClient(echo_oracle.url))

        oracle_tokens = run_tasks(tasks, adapter=oracle_adapter)
        iut_tokens = run_tasks(tasks, adapter=iut_adapter)

        pipeline = ComparisonPipeline()
        for oracle_tok, iut_tok in zip(oracle_tokens, iut_tokens, strict=True):
            result = pipeline.compare(oracle_tok, iut_tok)
            assert result.status == TaskStatus.OK
            assert result.layer == 1  # identity match (same echo)

    def test_run_tasks_default_adapter_still_works(self) -> None:
        """run_tasks with no adapter uses WolframAdapter stub (not HTTP)."""
        tasks = load_toml_tasks(Path("tests/fixtures/tracer.toml"))
        tokens = run_tasks(tasks)
        assert len(tokens) == 2
        assert all(t.status == TaskStatus.OK for t in tokens)
