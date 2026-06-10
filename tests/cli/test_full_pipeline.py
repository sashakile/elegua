"""Red-phase tests for --full-pipeline diagnostic mode (elegua-kaqt).

These tests define the CLI contract for the future ``elegua run --full-pipeline``
command. They should fail until the feature is implemented (elegua-t5ih).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.xfail(
    strict=True,
    reason="elegua run --full-pipeline not yet implemented (elegua-t5ih)",
)

FIXTURE = """
[meta]
id = "full-pipeline-matrix"
description = "Full-pipeline concordance fixture"
tags = ["full-pipeline"]

[matrix]
backend = ["sympy", "wolfram"]

[[tests]]
id = "expand-basic"
description = "expand (x+1)^2"
tags = ["full-pipeline"]
operations = [
  { action = "expand", args = { expr = "(x+1)^2" } },
]
""".strip()


def _write_fixture_tree(tmp_path: Path) -> Path:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "matrix.toml").write_text(FIXTURE, encoding="utf-8")
    return fixtures


_VERDICT_TOKENS = {"PASS", "FAIL", "AGREE", "DISAGREE", "ERROR"}


def _run_full_pipeline(fixtures: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "elegua", "run", "--full-pipeline", str(fixtures)],
        check=False,
        text=True,
        capture_output=True,
        timeout=30,
    )


def test_full_pipeline_exits_zero(tmp_path: Path):
    fixtures = _write_fixture_tree(tmp_path)
    result = _run_full_pipeline(fixtures)
    assert result.returncode == 0, result.stderr


def test_full_pipeline_stdout_has_concordance_header(tmp_path: Path):
    fixtures = _write_fixture_tree(tmp_path)
    result = _run_full_pipeline(fixtures)
    assert result.returncode == 0, result.stderr
    stdout = result.stdout
    assert "fixture" in stdout
    assert "backend" in stdout
    assert "verdict" in stdout


def test_full_pipeline_concordance_rows_contain_verdict_value(tmp_path: Path):
    fixtures = _write_fixture_tree(tmp_path)
    result = _run_full_pipeline(fixtures)
    assert result.returncode == 0, result.stderr
    stdout = result.stdout
    tokens_found = _VERDICT_TOKENS & set(stdout.split())
    assert tokens_found, f"expected a verdict token {_VERDICT_TOKENS} in stdout, got: {stdout!r}"


def test_full_pipeline_concordance_has_row_per_fixture_backend(tmp_path: Path):
    fixtures = _write_fixture_tree(tmp_path)
    result = _run_full_pipeline(fixtures)
    assert result.returncode == 0, result.stderr
    stdout = result.stdout
    # Matrix has 1 test x 2 backends -> 2 data rows
    assert "sympy" in stdout
    assert "wolfram" in stdout
    lines = [line for line in stdout.splitlines() if "expand-basic" in line]
    assert len(lines) == 2, f"expected 2 rows (one per backend), got: {lines}"
