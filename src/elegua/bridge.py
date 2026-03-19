"""Bridge loader for sxAct-format TOML test files.

Parses the rich sxAct test format (meta, setup, tests with operations
and expected outcomes) into structured data models, and provides
conversion to flat EleguaTask sequences.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from elegua.errors import SchemaError
from elegua.task import EleguaTask


@dataclass(frozen=True)
class TestFileMeta:
    """File-level metadata."""

    __test__ = False

    id: str
    description: str
    tags: list[str] = field(default_factory=list)
    layer: int = 1
    oracle_is_axiom: bool = True
    skip: str | None = None


@dataclass(frozen=True)
class Operation:
    """A single operation in a setup or test block."""

    action: str
    args: dict[str, Any] = field(default_factory=dict)
    store_as: str | None = None


@dataclass(frozen=True)
class Expected:
    """Expected outcome for a test case."""

    expr: str | None = None
    normalized: str | None = None
    value: int | float | str | None = None
    is_zero: bool | None = None
    properties: dict[str, Any] | None = None
    comparison_tier: int | None = None
    expect_error: bool | None = None


@dataclass(frozen=True)
class TestCase:
    """A named test case with operations and optional expected outcome."""

    __test__ = False

    id: str
    description: str
    operations: list[Operation]
    expected: Expected | None = None
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    skip: str | None = None
    oracle_is_axiom: bool | None = None


@dataclass(frozen=True)
class TestFile:
    """Parsed sxAct-format test file."""

    __test__ = False

    meta: TestFileMeta
    setup: list[Operation] = field(default_factory=list)
    tests: list[TestCase] = field(default_factory=list)

    def to_tasks(self) -> list[EleguaTask]:
        """Flatten into EleguaTask sequences (setup first, then tests in order).

        Operation args become the task payload. If an operation has store_as,
        it is included in the payload as ``_store_as``.
        """
        tasks: list[EleguaTask] = []
        for op in self.setup:
            tasks.append(_op_to_task(op))
        for test in self.tests:
            for op in test.operations:
                tasks.append(_op_to_task(op))
        return tasks


def _op_to_task(op: Operation) -> EleguaTask:
    payload = dict(op.args)
    if op.store_as is not None:
        payload["_store_as"] = op.store_as
    return EleguaTask(action=op.action, payload=payload)


def _parse_operation(raw: dict[str, Any]) -> Operation:
    action = raw.get("action")
    if not action:
        raise SchemaError("operation missing required 'action' field")
    store_as = raw.get("store_as")
    if store_as is not None and not re.match(r"^[a-zA-Z_]\w*$", store_as):
        raise SchemaError(
            f"store_as={store_as!r} is not a valid identifier (must match [a-zA-Z_]\\w*)"
        )
    return Operation(
        action=action,
        args=raw.get("args", {}),
        store_as=store_as,
    )


def _parse_expected(raw: dict[str, Any]) -> Expected:
    return Expected(
        expr=raw.get("expr"),
        normalized=raw.get("normalized"),
        value=raw.get("value"),
        is_zero=raw.get("is_zero"),
        properties=raw.get("properties"),
        comparison_tier=raw.get("comparison_tier"),
        expect_error=raw.get("expect_error"),
    )


def _parse_test(raw: dict[str, Any], index: int) -> TestCase:
    test_id = raw.get("id")
    if not test_id:
        raise SchemaError(f"tests[{index}] missing required 'id' field")
    description = raw.get("description")
    if not description:
        raise SchemaError(f"tests[{index}] missing required 'description' field")
    operations_raw = raw.get("operations", [])
    if not operations_raw:
        raise SchemaError(f"tests[{index}] must have at least one operation")
    return TestCase(
        id=test_id,
        description=description,
        operations=[_parse_operation(op) for op in operations_raw],
        expected=_parse_expected(raw["expected"]) if "expected" in raw else None,
        tags=raw.get("tags", []),
        dependencies=raw.get("dependencies", []),
        skip=raw.get("skip"),
        oracle_is_axiom=raw.get("oracle_is_axiom"),
    )


def load_sxact_toml(path: Path) -> TestFile:
    """Load an sxAct-format TOML test file.

    Raises SchemaError if the file is missing required fields.
    """
    with open(path, "rb") as f:
        try:
            data = tomllib.load(f)
        except tomllib.TOMLDecodeError as exc:
            raise SchemaError(f"{path}: invalid TOML: {exc}") from exc

    if "meta" not in data:
        raise SchemaError(f"{path}: missing required 'meta' section")

    meta_raw = data["meta"]
    if "id" not in meta_raw:
        raise SchemaError(f"{path}: meta missing required 'id' field")
    if "description" not in meta_raw:
        raise SchemaError(f"{path}: meta missing required 'description' field")

    meta = TestFileMeta(
        id=meta_raw["id"],
        description=meta_raw["description"],
        tags=meta_raw.get("tags", []),
        layer=meta_raw.get("layer", 1),
        oracle_is_axiom=meta_raw.get("oracle_is_axiom", True),
        skip=meta_raw.get("skip"),
    )

    setup = [_parse_operation(op) for op in data.get("setup", [])]
    tests = [_parse_test(t, i) for i, t in enumerate(data.get("tests", []))]

    return TestFile(meta=meta, setup=setup, tests=tests)
