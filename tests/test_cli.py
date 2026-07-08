"""CLI tests for elegua commands."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def test_run_legacy_tracer_help() -> None:
    """--help shows run subcommand."""
    result = subprocess.run(
        [sys.executable, "-m", "elegua", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert result.returncode == 0
    assert "run" in result.stdout
    assert "coverage" in result.stdout


def test_run_legacy_tracer_passes() -> None:
    """Legacy [[tasks]] format fixture passes with wolfram adapter."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "elegua",
            "run",
            str(FIXTURES / "tracer.toml"),
            "--oracle",
            "wolfram",
            "--iut",
            "wolfram",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "PASS" in result.stdout
    assert "tracer" in result.stdout


def test_run_bridge_format_passes() -> None:
    """Bridge format fixture passes with wolfram adapter."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "elegua",
            "run",
            str(FIXTURES / "sxact_basic.toml"),
            "--oracle",
            "wolfram",
            "--iut",
            "wolfram",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "canon_symmetric" in result.stdout
    assert "registry_check" in result.stdout


def test_run_missing_file() -> None:
    """Non-existent fixture reports error."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "elegua",
            "run",
            "nonexistent.toml",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert result.returncode == 1
    assert "not a file" in result.stderr


def test_run_unknown_adapter() -> None:
    """Unknown adapter name exits with error."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "elegua",
            "run",
            str(FIXTURES / "tracer.toml"),
            "--oracle",
            "nosuch",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert result.returncode == 1
    assert "Unknown adapter" in result.stderr


def test_all_no_longer_exports_deprecated() -> None:
    """load_toml_tasks and run_tasks removed from __all__."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from elegua import *; print('load_toml_tasks' in dir()); print('run_tasks' in dir())",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    lines = result.stdout.strip().splitlines()
    assert lines[0] == "False"
    assert lines[1] == "False"
