"""Tests for TOML test loader and minimal runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from elegua.adapter import WolframAdapter
from elegua.runner import load_toml_tasks, run_tasks
from elegua.task import EleguaTask, TaskStatus

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_toml_tasks():
    tasks = load_toml_tasks(FIXTURES / "tracer.toml")
    assert len(tasks) == 2
    assert all(isinstance(t, EleguaTask) for t in tasks)
    assert tasks[0].action == "DefTensor"
    assert tasks[1].action == "Contract"


def test_load_toml_meta():
    tasks = load_toml_tasks(FIXTURES / "tracer.toml")
    assert all(t.status == TaskStatus.PENDING for t in tasks)


def test_run_tasks_all_ok():
    tasks = load_toml_tasks(FIXTURES / "tracer.toml")
    results = run_tasks(tasks)
    assert len(results) == 2
    assert all(r.status == TaskStatus.OK for r in results)


def test_run_tasks_produces_results():
    tasks = load_toml_tasks(FIXTURES / "tracer.toml")
    results = run_tasks(tasks)
    assert all(r.result is not None for r in results)


def test_run_tasks_accepts_explicit_adapter():
    tasks = load_toml_tasks(FIXTURES / "tracer.toml")
    adapter = WolframAdapter()
    results = run_tasks(tasks, adapter=adapter)
    assert all(r.status == TaskStatus.OK for r in results)


def test_load_toml_missing_tasks_key(tmp_path: Path):
    bad = tmp_path / "bad.toml"
    bad.write_text('[meta]\nname = "oops"\n')
    with pytest.raises(ValueError, match="missing required 'tasks' array"):
        load_toml_tasks(bad)


def test_load_toml_missing_action_field(tmp_path: Path):
    bad = tmp_path / "bad.toml"
    bad.write_text('[[tasks]]\n[tasks.payload]\nfoo = "bar"\n')
    with pytest.raises(ValueError, match="missing required field 'action'"):
        load_toml_tasks(bad)
