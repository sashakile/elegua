"""Red-phase tests for fixture coverage reports (elegua-29d1).

These tests define the CLI contract for the future ``elegua coverage`` command.
They should fail until coverage reporting is implemented.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

FIXTURE = """
[meta]
id = "coverage-matrix"
description = "Coverage report matrix fixture"
tags = ["coverage"]

[matrix]
adapter = ["sympy", "wolfram"]
action = ["expand", "factor"]

[[tests]]
id = "sympy-expand"
description = "one covered matrix cell"
tags = ["coverage"]
adapter = "sympy"
action = "expand"
operations = [
  { action = "expand", args = { expr = "(x+1)^2" } },
]
""".strip()


def _write_fixture_tree(tmp_path: Path) -> Path:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "coverage.toml").write_text(FIXTURE, encoding="utf-8")
    return fixtures


def _run_coverage(fixtures: Path, output_dir: Path, axis: str = "adapter,action"):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "elegua",
            "coverage",
            str(fixtures),
            "--axis",
            axis,
            "--output-dir",
            str(output_dir),
        ],
        check=False,
        text=True,
        capture_output=True,
    )


def test_coverage_command_writes_csv_and_markdown(tmp_path: Path):
    fixtures = _write_fixture_tree(tmp_path)
    output_dir = tmp_path / "coverage-out"

    result = _run_coverage(fixtures, output_dir)

    assert result.returncode == 0, result.stderr
    assert (output_dir / "coverage.csv").is_file()
    assert (output_dir / "coverage.md").is_file()


def test_coverage_outputs_flag_zero_coverage_cells(tmp_path: Path):
    fixtures = _write_fixture_tree(tmp_path)
    output_dir = tmp_path / "coverage-out"

    result = _run_coverage(fixtures, output_dir)

    assert result.returncode == 0, result.stderr
    csv_text = (output_dir / "coverage.csv").read_text(encoding="utf-8")
    md_text = (output_dir / "coverage.md").read_text(encoding="utf-8")
    assert "wolfram,factor,0" in csv_text
    assert "wolfram" in md_text
    assert "factor" in md_text
    assert "0" in md_text or "⚠" in md_text


def test_coverage_axis_configuration_controls_rows_and_columns(tmp_path: Path):
    fixtures = _write_fixture_tree(tmp_path)
    output_dir = tmp_path / "coverage-out"

    result = _run_coverage(fixtures, output_dir, axis="action,adapter")

    assert result.returncode == 0, result.stderr
    with (output_dir / "coverage.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["action", "adapter", "count"]
    assert ["expand", "sympy", "1"] in rows
    assert ["factor", "wolfram", "0"] in rows
    md_text = (output_dir / "coverage.md").read_text(encoding="utf-8")
    assert "| action | adapter | count |" in md_text
