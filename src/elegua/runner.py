"""TOML test loader and minimal runner."""

from __future__ import annotations

import tomllib
from pathlib import Path

from elegua.adapter import Adapter, WolframAdapter
from elegua.models import ValidationToken
from elegua.task import EleguaTask


def load_toml_tasks(path: Path) -> list[EleguaTask]:
    """Load tasks from a TOML test file.

    Raises ValueError if the TOML file has no 'tasks' key.
    """
    with open(path, "rb") as f:
        data = tomllib.load(f)

    if "tasks" not in data:
        raise ValueError(f"{path}: missing required 'tasks' array")

    tasks = data["tasks"]
    return [
        EleguaTask(
            action=t.get("action") or _missing_field(path, i, "action"),
            payload=t.get("payload", {}),
        )
        for i, t in enumerate(tasks)
    ]


def _missing_field(path: Path, index: int, field: str) -> str:
    raise ValueError(f"{path}: tasks[{index}] missing required field '{field}'")


def run_tasks(
    tasks: list[EleguaTask],
    adapter: Adapter | None = None,
) -> list[ValidationToken]:
    """Execute tasks through an adapter and return ValidationTokens.

    If no adapter is provided, defaults to WolframAdapter (stub).
    """
    if adapter is None:
        adapter = WolframAdapter()
    return [adapter.execute(task) for task in tasks]
