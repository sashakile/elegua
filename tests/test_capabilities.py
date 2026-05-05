"""Red-phase tests for adapter capability declarations and negotiation (elegua-ef7).

All tests MUST FAIL until elegua.capabilities is implemented and the
Adapter.capabilities property and TestFileMeta capability fields are added.
See: elegua-ef7, elegua-r2x, elegua-4z2.
"""

from __future__ import annotations

import tempfile
import textwrap
from pathlib import Path

import pytest

pytest.importorskip(
    "elegua.capabilities",
    reason="elegua.capabilities not yet implemented (elegua-r2x)",
)

from elegua.adapter import Adapter
from elegua.bridge import Operation, TestCase, TestFile, TestFileMeta, load_test_file
from elegua.capabilities import check_capabilities
from elegua.models import ValidationToken
from elegua.task import EleguaTask, TaskStatus

# ---------------------------------------------------------------------------
# Stub adapters
# ---------------------------------------------------------------------------


class FullAdapter(Adapter):
    """Adapter advertising gradient, deterministic, and seedable capabilities."""

    @property
    def adapter_id(self) -> str:
        return "full"

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset({"gradient", "deterministic", "seedable"})

    def execute(self, task: EleguaTask) -> ValidationToken:
        return ValidationToken(adapter_id=self.adapter_id, status=TaskStatus.OK, result={})


class LimitedAdapter(Adapter):
    """Adapter with no declared capabilities."""

    @property
    def adapter_id(self) -> str:
        return "limited"

    def execute(self, task: EleguaTask) -> ValidationToken:
        return ValidationToken(adapter_id=self.adapter_id, status=TaskStatus.OK, result={})


# ---------------------------------------------------------------------------
# Adapter.capabilities property
# ---------------------------------------------------------------------------


def test_adapter_declares_capabilities():
    adapter = FullAdapter()
    assert "gradient" in adapter.capabilities
    assert "deterministic" in adapter.capabilities
    assert "seedable" in adapter.capabilities


def test_adapter_default_capabilities_is_empty_frozenset():
    adapter = LimitedAdapter()
    assert adapter.capabilities == frozenset()


# ---------------------------------------------------------------------------
# TestFileMeta capability fields
# ---------------------------------------------------------------------------


def test_test_file_meta_requires_field():
    meta = TestFileMeta(id="t1", description="test", requires=frozenset({"gradient"}))
    assert "gradient" in meta.requires


def test_test_file_meta_prefers_field():
    meta = TestFileMeta(id="t1", description="test", prefers=frozenset({"seedable"}))
    assert "seedable" in meta.prefers


def test_test_file_meta_tier_overrides_exempts_capability():
    meta = TestFileMeta(
        id="t1",
        description="test",
        requires=frozenset({"seedable"}),
        tier_overrides={"oracle": frozenset({"seedable"})},
    )
    assert "seedable" in meta.tier_overrides["oracle"]


def test_test_file_meta_defaults_empty():
    meta = TestFileMeta(id="t1", description="test")
    assert meta.requires == frozenset()
    assert meta.prefers == frozenset()
    assert meta.tier_overrides == {}


# ---------------------------------------------------------------------------
# check_capabilities function
# ---------------------------------------------------------------------------


def test_check_capabilities_passes_when_all_present():
    ok, missing = check_capabilities(
        adapter_capabilities=frozenset({"gradient", "deterministic"}),
        requires=frozenset({"gradient"}),
    )
    assert ok is True
    assert missing == frozenset()


def test_check_capabilities_fails_when_capability_missing():
    ok, missing = check_capabilities(
        adapter_capabilities=frozenset({"deterministic"}),
        requires=frozenset({"gradient", "deterministic"}),
    )
    assert ok is False
    assert "gradient" in missing
    assert "deterministic" not in missing


def test_check_capabilities_empty_requires_always_passes():
    ok, missing = check_capabilities(
        adapter_capabilities=frozenset(),
        requires=frozenset(),
    )
    assert ok is True
    assert missing == frozenset()


def test_check_capabilities_tier_override_exempts_requirement():
    ok, missing = check_capabilities(
        adapter_capabilities=frozenset(),
        requires=frozenset({"seedable"}),
        exempts=frozenset({"seedable"}),
    )
    assert ok is True
    assert missing == frozenset()


def test_check_capabilities_partial_exemption_still_checks_others():
    ok, missing = check_capabilities(
        adapter_capabilities=frozenset(),
        requires=frozenset({"seedable", "gradient"}),
        exempts=frozenset({"seedable"}),
    )
    assert ok is False
    assert "gradient" in missing
    assert "seedable" not in missing


# ---------------------------------------------------------------------------
# MultiTierRunner integration
# ---------------------------------------------------------------------------


def _make_test_file(
    requires: frozenset[str],
    tier_overrides: dict[str, frozenset[str]] | None = None,
) -> TestFile:
    meta = TestFileMeta(
        id="cap-test",
        description="Capability test fixture",
        requires=requires,
        tier_overrides=tier_overrides or {},
    )
    test_case = TestCase(
        id="tc1",
        description="A test",
        operations=[Operation(action="eval", args={"expression": "1+1"})],
    )
    return TestFile(meta=meta, tests=[test_case])


def test_multitier_skips_iut_lacking_required_capability():
    from elegua.multitier import MultiTierRunner

    oracle = FullAdapter()
    iut = LimitedAdapter()  # no capabilities

    test_file = _make_test_file(requires=frozenset({"gradient"}))

    with MultiTierRunner(oracle=oracle, iut=iut) as runner:
        results = runner.verify(test_file)

    assert len(results) == 1
    result = results[0]
    assert result.skipped is True
    assert result.skip_reason is not None
    assert "gradient" in result.skip_reason


def test_multitier_passes_when_both_adapters_have_required_capabilities():
    from elegua.multitier import MultiTierRunner

    oracle = FullAdapter()
    iut = FullAdapter()

    test_file = _make_test_file(requires=frozenset({"gradient", "deterministic"}))

    with MultiTierRunner(oracle=oracle, iut=iut) as runner:
        results = runner.verify(test_file)

    assert len(results) == 1
    result = results[0]
    assert result.skipped is False


def test_multitier_skips_oracle_lacking_required_capability():
    from elegua.multitier import MultiTierRunner

    oracle = LimitedAdapter()  # no capabilities
    iut = FullAdapter()

    test_file = _make_test_file(requires=frozenset({"gradient"}))

    with MultiTierRunner(oracle=oracle, iut=iut) as runner:
        results = runner.verify(test_file)

    assert len(results) == 1
    result = results[0]
    assert result.skipped is True
    assert result.skip_reason is not None
    assert "gradient" in result.skip_reason


def test_multitier_tier_override_exempts_oracle_from_seedable():
    from elegua.multitier import MultiTierRunner

    oracle = LimitedAdapter()  # no capabilities, but exempted from seedable
    iut = FullAdapter()  # has seedable

    test_file = _make_test_file(
        requires=frozenset({"seedable"}),
        tier_overrides={"oracle": frozenset({"seedable"})},
    )

    with MultiTierRunner(oracle=oracle, iut=iut) as runner:
        results = runner.verify(test_file)

    # Oracle is exempt, IUT has seedable → fixture runs
    assert len(results) == 1
    result = results[0]
    assert result.skipped is False


def test_multitier_no_requires_always_runs():
    from elegua.multitier import MultiTierRunner

    oracle = LimitedAdapter()
    iut = LimitedAdapter()

    test_file = _make_test_file(requires=frozenset())

    with MultiTierRunner(oracle=oracle, iut=iut) as runner:
        results = runner.verify(test_file)

    assert len(results) == 1
    assert results[0].skipped is False


# ---------------------------------------------------------------------------
# TOML fixture parsing
# ---------------------------------------------------------------------------


def test_toml_fixture_requires_parsed():
    toml = textwrap.dedent("""\
        [meta]
        id = "cap-test"
        description = "Tests capability requires"
        requires = ["gradient", "deterministic"]

        [[tests]]
        id = "tc1"
        description = "A test"
        [[tests.operations]]
        action = "eval"
        [tests.operations.args]
        expression = "1+1"
    """)
    with tempfile.NamedTemporaryFile(suffix=".toml", mode="w", delete=False) as f:
        f.write(toml)
        tmp_path = Path(f.name)

    try:
        test_file = load_test_file(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    assert "gradient" in test_file.meta.requires
    assert "deterministic" in test_file.meta.requires


def test_toml_fixture_prefers_parsed():
    toml = textwrap.dedent("""\
        [meta]
        id = "cap-test"
        description = "Tests capability prefers"
        prefers = ["seedable"]

        [[tests]]
        id = "tc1"
        description = "A test"
        [[tests.operations]]
        action = "eval"
        [tests.operations.args]
        expression = "1+1"
    """)
    with tempfile.NamedTemporaryFile(suffix=".toml", mode="w", delete=False) as f:
        f.write(toml)
        tmp_path = Path(f.name)

    try:
        test_file = load_test_file(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    assert "seedable" in test_file.meta.prefers


def test_toml_fixture_tier_override_parsed():
    toml = textwrap.dedent("""\
        [meta]
        id = "cap-test"
        description = "Tests tier override"
        requires = ["seedable"]

        [meta.tier_overrides.oracle]
        exempts = ["seedable"]

        [[tests]]
        id = "tc1"
        description = "A test"
        [[tests.operations]]
        action = "eval"
        [tests.operations.args]
        expression = "1+1"
    """)
    with tempfile.NamedTemporaryFile(suffix=".toml", mode="w", delete=False) as f:
        f.write(toml)
        tmp_path = Path(f.name)

    try:
        test_file = load_test_file(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    assert "oracle" in test_file.meta.tier_overrides
    assert "seedable" in test_file.meta.tier_overrides["oracle"]
