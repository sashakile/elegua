"""Tests for TOML test loader and minimal runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from elegua.adapter import Adapter, WolframAdapter
from elegua.errors import SchemaError
from elegua.models import ValidationToken
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


def test_run_tasks_returns_tokens():
    tasks = load_toml_tasks(FIXTURES / "tracer.toml")
    tokens = run_tasks(tasks)
    assert len(tokens) == 2
    assert all(isinstance(t, ValidationToken) for t in tokens)
    assert all(t.status == TaskStatus.OK for t in tokens)


def test_run_tasks_produces_results():
    tasks = load_toml_tasks(FIXTURES / "tracer.toml")
    tokens = run_tasks(tasks)
    assert all(t.result is not None for t in tokens)


def test_run_tasks_accepts_explicit_adapter():
    tasks = load_toml_tasks(FIXTURES / "tracer.toml")
    adapter = WolframAdapter()
    tokens = run_tasks(tasks, adapter=adapter)
    assert all(t.status == TaskStatus.OK for t in tokens)


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


def test_run_tasks_empty_list():
    assert run_tasks([]) == []


def test_load_toml_empty_tasks_array(tmp_path: Path):
    empty = tmp_path / "empty.toml"
    empty.write_text("tasks = []\n")
    tasks = load_toml_tasks(empty)
    assert tasks == []


def test_load_toml_empty_action_treated_as_missing(tmp_path: Path):
    bad = tmp_path / "bad.toml"
    bad.write_text('[[tasks]]\naction = ""\n')
    with pytest.raises(ValueError, match="missing required field 'action'"):
        load_toml_tasks(bad)


def test_run_tasks_calls_adapter_lifecycle():
    """run_tasks brackets execution with initialize/teardown."""

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
    tasks = [
        EleguaTask(action="A", payload={}),
        EleguaTask(action="B", payload={}),
    ]
    run_tasks(tasks, adapter=adapter)
    assert adapter.calls == ["initialize", "execute:A", "execute:B", "teardown"]


def test_load_malformed_toml(tmp_path):
    f = tmp_path / "bad.toml"
    f.write_text("this is not valid [[[ toml")
    with pytest.raises(SchemaError, match="invalid TOML"):
        load_toml_tasks(f)
