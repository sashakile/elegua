"""Red-phase tests for matrix expansion and inheritance (elegua-i67n).

These tests define the contract for the future ``elegua.matrix`` module.
They should fail until elegua-ouqt is implemented.
"""

from __future__ import annotations

import tomllib

import pytest

pytest.importorskip(
    "elegua.matrix",
    reason="elegua.matrix not yet implemented (elegua-ouqt)",
)

from elegua.errors import SchemaError
from elegua.matrix import expand_matrix, resolve_inheritance

# --- Fixtures ---

_MATRIX_TOML = """
[meta]
id = "math-suite"
description = "Matrix test suite"
tags = ["math"]

[matrix]
adapter = ["sympy", "wolfram"]
action = ["expand", "factor"]

[[tests]]
id = "basic"
description = "basic operation"
operations = [
  { action = "expand", args = { expr = "(x+1)^2" } },
]
""".strip()

_BASE_TOML = """
[meta]
id = "base-fixture"
description = "Base fixture"
tags = ["base"]

[[tests]]
id = "base-test"
description = "base test"
operations = [
  { action = "expand", args = { expr = "x^2" } },
]
""".strip()

_DERIVED_TOML = """
[meta]
id = "derived-fixture"
description = "Derived fixture"
extends = "base-fixture"
tags = ["derived"]

[[tests]]
id = "extra-test"
description = "extra test"
operations = [
  { action = "factor", args = { expr = "x^2 - 1" } },
]
""".strip()

_CYCLE_A_TOML = """
[meta]
id = "fixture-a"
description = "Fixture A"
extends = "fixture-b"

[[tests]]
id = "test-a"
description = "test"
operations = [{ action = "expand", args = { expr = "x" } }]
""".strip()

_CYCLE_B_TOML = """
[meta]
id = "fixture-b"
description = "Fixture B"
extends = "fixture-a"

[[tests]]
id = "test-b"
description = "test"
operations = [{ action = "expand", args = { expr = "y" } }]
""".strip()


def _load(toml_str: str) -> dict:
    return tomllib.loads(toml_str)


# --- Matrix expansion ---


def test_matrix_expansion_produces_cartesian_product_count():
    raw = _load(_MATRIX_TOML)
    # 2 adapters x 2 actions = 4 combinations
    expanded = expand_matrix(raw)
    assert len(expanded) == 4


def test_matrix_expansion_names_include_dimension_values():
    raw = _load(_MATRIX_TOML)
    expanded = expand_matrix(raw)
    ids = {e["meta"]["id"] for e in expanded}
    # Each expanded variant must encode its dimension values
    assert any("sympy" in eid for eid in ids)
    assert any("wolfram" in eid for eid in ids)
    assert any("expand" in eid for eid in ids)
    assert any("factor" in eid for eid in ids)


def test_matrix_expansion_names_are_stable():
    raw = _load(_MATRIX_TOML)
    first = [e["meta"]["id"] for e in expand_matrix(raw)]
    second = [e["meta"]["id"] for e in expand_matrix(raw)]
    assert first == second


def test_matrix_expansion_propagates_parent_tags():
    raw = _load(_MATRIX_TOML)
    expanded = expand_matrix(raw)
    for variant in expanded:
        assert "math" in variant["meta"].get("tags", [])


# --- Inheritance ---


def test_inheritance_merges_test_cases():
    base = _load(_BASE_TOML)
    derived = _load(_DERIVED_TOML)
    registry = {
        base["meta"]["id"]: base,
        derived["meta"]["id"]: derived,
    }
    resolved = resolve_inheritance(registry, "derived-fixture")
    test_ids = {t["id"] for t in resolved.get("tests", [])}
    assert "base-test" in test_ids
    assert "extra-test" in test_ids


def test_inheritance_propagates_tags_from_base():
    base = _load(_BASE_TOML)
    derived = _load(_DERIVED_TOML)
    registry = {
        base["meta"]["id"]: base,
        derived["meta"]["id"]: derived,
    }
    resolved = resolve_inheritance(registry, "derived-fixture")
    tags = set(resolved["meta"].get("tags", []))
    assert "base" in tags
    assert "derived" in tags


def test_inheritance_missing_parent_raises_schema_error():
    derived = _load(_DERIVED_TOML)
    registry = {derived["meta"]["id"]: derived}  # base not present
    with pytest.raises(SchemaError, match="base-fixture"):
        resolve_inheritance(registry, "derived-fixture")


# --- Cycle detection ---


def test_cycle_detection_raises_schema_error():
    a = _load(_CYCLE_A_TOML)
    b = _load(_CYCLE_B_TOML)
    registry = {
        a["meta"]["id"]: a,
        b["meta"]["id"]: b,
    }
    with pytest.raises(SchemaError, match=r"(?i)cycle"):
        resolve_inheritance(registry, "fixture-a")
