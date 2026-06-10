"""Red-phase tests for CLI filter flags (elegua-wp8s).

These tests define the contract for --tag, --capability, --adapter,
--changed, and --last-run-failures on the future ``elegua run`` subcommand.
They should fail until elegua-38bh is implemented.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.xfail(
    strict=True,
    reason="elegua run filters not yet implemented (elegua-38bh)",
)

# algebra fixture: tagged 'algebra', no special capability requirements
_FIXTURE_ALGEBRA = """
[meta]
id = "algebra-fixture"
description = "Algebra fixture tagged algebra"
tags = ["algebra"]

[[tests]]
id = "algebra-basic"
description = "expand (x+1)^2"
tags = ["algebra"]
operations = [
  { action = "expand", args = { expr = "(x+1)^2" } },
]
""".strip()

# calculus fixture: tagged 'calculus', requires 'gradient' capability
_FIXTURE_CALCULUS = """
[meta]
id = "calculus-fixture"
description = "Calculus fixture tagged calculus"
tags = ["calculus"]
requires = ["gradient"]

[[tests]]
id = "calculus-basic"
description = "differentiate x^2"
tags = ["calculus"]
operations = [
  { action = "diff", args = { expr = "x^2", var = "x" } },
]
""".strip()


def _write_fixtures(tmp_path: Path) -> Path:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "algebra.toml").write_text(_FIXTURE_ALGEBRA, encoding="utf-8")
    (fixtures / "calculus.toml").write_text(_FIXTURE_CALCULUS, encoding="utf-8")
    return fixtures


def _run(fixtures: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "elegua", "run", str(fixtures), *extra],
        check=False,
        text=True,
        capture_output=True,
        timeout=30,
    )


def test_tag_filter_runs_only_matching_fixtures(tmp_path: Path):
    fixtures = _write_fixtures(tmp_path)
    result = _run(fixtures, "--tag", "algebra")
    assert result.returncode == 0, result.stderr
    assert "algebra-basic" in result.stdout
    assert "calculus-basic" not in result.stdout


def test_adapter_filter_selects_runtime_adapter(tmp_path: Path):
    # --adapter selects which adapter engine the runner uses at runtime;
    # it is not a per-fixture declaration in the TOML schema.
    fixtures = _write_fixtures(tmp_path)
    result = _run(fixtures, "--adapter", "sympy")
    assert result.returncode == 0, result.stderr
    # All fixtures run, but only through the sympy adapter
    assert "algebra-basic" in result.stdout
    assert "sympy" in result.stdout


def test_capability_filter_excludes_fixtures_lacking_required_capability(tmp_path: Path):
    # _FIXTURE_CALCULUS declares requires = ["gradient"]; only adapters that
    # advertise the 'gradient' capability should be selected for it.
    # With --capability gradient, fixtures requiring capabilities not met are excluded.
    fixtures = _write_fixtures(tmp_path)
    result = _run(fixtures, "--capability", "gradient")
    assert result.returncode == 0, result.stderr
    # algebra-basic has no requires -> excluded when filtering to 'gradient' only
    assert "algebra-basic" not in result.stdout
    # calculus-basic requires gradient -> included
    assert "calculus-basic" in result.stdout


def test_changed_filter_flag_is_accepted(tmp_path: Path):
    fixtures = _write_fixtures(tmp_path)
    result = _run(fixtures, "--changed")
    assert "unrecognized" not in result.stderr.lower(), result.stderr
    assert result.returncode == 0, result.stderr


def test_changed_filter_excludes_unmodified_fixtures(tmp_path: Path):
    # tmp_path fixtures are untracked by git and have no prior baseline;
    # the --changed filter should produce no run output.
    fixtures = _write_fixtures(tmp_path)
    result = _run(fixtures, "--changed")
    assert result.returncode == 0, result.stderr
    stdout = result.stdout
    assert "algebra-basic" not in stdout and "calculus-basic" not in stdout


def test_last_run_failures_runs_nothing_without_prior_history(tmp_path: Path):
    fixtures = _write_fixtures(tmp_path)
    result = _run(fixtures, "--last-run-failures")
    assert "unrecognized" not in result.stderr.lower(), result.stderr
    assert result.returncode == 0, result.stderr
    # No prior run history -> no failures to rerun
    assert "algebra-basic" not in result.stdout
    assert "calculus-basic" not in result.stdout
