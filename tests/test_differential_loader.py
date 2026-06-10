"""Red-phase tests for differential fixture loading (elegua-bon).

These tests define the contract for the future ``elegua.differential`` loader.
They should fail until elegua-pvr is implemented.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip(
    "elegua.differential",
    reason="elegua.differential not yet implemented (elegua-pvr)",
)

from elegua.differential import DifferentialFixture, Evaluation, load_differential_fixture
from elegua.errors import SchemaError

_TWO_EVAL_TOML = """
[meta]
id = "two-eval-fixture"
description = "Two-evaluation differential fixture"
tags = ["differential"]

[[evaluations]]
id = "eval-a"
operations = [
  { action = "expand", args = { expr = "(x+1)^2" } },
]

[[evaluations]]
id = "eval-b"
operations = [
  { action = "expand", args = { expr = "(x+1)^2" } },
]

[relation]
type = "equality"
""".strip()

_MULTI_EVAL_TOML = """
[meta]
id = "multi-eval-fixture"
description = "Three-evaluation differential fixture"

[[evaluations]]
id = "eval-1"
operations = [{ action = "expand", args = { expr = "x^2" } }]

[[evaluations]]
id = "eval-2"
operations = [{ action = "expand", args = { expr = "x^2" } }]

[[evaluations]]
id = "eval-3"
operations = [{ action = "expand", args = { expr = "x^2" } }]

[relation]
type = "linear_combination"
coefficients = { "eval-1" = 1.0, "eval-2" = -1.0, "eval-3" = 0.5 }
""".strip()

_CROSS_ADAPTER_TOML = """
[meta]
id = "cross-adapter-fixture"
description = "Cross-adapter differential fixture"

[[evaluations]]
id = "sympy-eval"
adapter = "sympy"
operations = [{ action = "expand", args = { expr = "(x+1)^2" } }]

[[evaluations]]
id = "wolfram-eval"
adapter = "wolfram"
operations = [{ action = "expand", args = { expr = "(x+1)^2" } }]

[relation]
type = "equality"
""".strip()

_MISSING_META_TOML = """
[[evaluations]]
id = "eval-a"
operations = [{ action = "expand", args = { expr = "x" } }]

[[evaluations]]
id = "eval-b"
operations = [{ action = "expand", args = { expr = "x" } }]

[relation]
type = "equality"
""".strip()

_SINGLE_EVAL_TOML = """
[meta]
id = "single-eval-fixture"
description = "Only one evaluation - invalid"

[[evaluations]]
id = "eval-a"
operations = [{ action = "expand", args = { expr = "x" } }]

[relation]
type = "equality"
""".strip()

_MISSING_RELATION_TOML = """
[meta]
id = "no-relation-fixture"
description = "No relation section - invalid"

[[evaluations]]
id = "eval-a"
operations = [{ action = "expand", args = { expr = "x" } }]

[[evaluations]]
id = "eval-b"
operations = [{ action = "expand", args = { expr = "x" } }]
""".strip()


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# --- Two-evaluation fixture ---


def test_loads_two_evaluation_differential_fixture(tmp_path: Path):
    path = _write(tmp_path, "two.toml", _TWO_EVAL_TOML)
    fixture = load_differential_fixture(path)
    assert isinstance(fixture, DifferentialFixture)


def test_two_evaluation_fixture_has_correct_meta(tmp_path: Path):
    path = _write(tmp_path, "two.toml", _TWO_EVAL_TOML)
    fixture = load_differential_fixture(path)
    assert fixture.meta.id == "two-eval-fixture"
    assert "differential" in fixture.meta.tags


def test_two_evaluation_fixture_has_two_evaluations(tmp_path: Path):
    path = _write(tmp_path, "two.toml", _TWO_EVAL_TOML)
    fixture = load_differential_fixture(path)
    assert len(fixture.evaluations) == 2
    assert all(isinstance(e, Evaluation) for e in fixture.evaluations)


def test_two_evaluation_fixture_preserves_evaluation_order(tmp_path: Path):
    path = _write(tmp_path, "two.toml", _TWO_EVAL_TOML)
    fixture = load_differential_fixture(path)
    # TOML array order must be preserved (affects execution dispatch order)
    assert [e.id for e in fixture.evaluations] == ["eval-a", "eval-b"]


def test_evaluation_adapter_defaults_to_none_when_not_specified(tmp_path: Path):
    path = _write(tmp_path, "two.toml", _TWO_EVAL_TOML)
    fixture = load_differential_fixture(path)
    # Evaluations without an explicit adapter field default to None (runtime selection)
    assert all(e.adapter is None for e in fixture.evaluations)


def test_two_evaluation_fixture_has_relation_type(tmp_path: Path):
    path = _write(tmp_path, "two.toml", _TWO_EVAL_TOML)
    fixture = load_differential_fixture(path)
    assert fixture.relation.type == "equality"


# --- Multi-evaluation fixture ---


def test_loads_multi_evaluation_fixture(tmp_path: Path):
    path = _write(tmp_path, "multi.toml", _MULTI_EVAL_TOML)
    fixture = load_differential_fixture(path)
    assert len(fixture.evaluations) == 3


def test_multi_evaluation_relation_carries_coefficients(tmp_path: Path):
    path = _write(tmp_path, "multi.toml", _MULTI_EVAL_TOML)
    fixture = load_differential_fixture(path)
    assert fixture.relation.type == "linear_combination"
    assert "eval-1" in fixture.relation.coefficients
    assert fixture.relation.coefficients["eval-1"] == 1.0


# --- Cross-adapter fixture ---


def test_cross_adapter_evaluations_each_name_an_adapter(tmp_path: Path):
    path = _write(tmp_path, "cross.toml", _CROSS_ADAPTER_TOML)
    fixture = load_differential_fixture(path)
    adapter_ids = {e.adapter for e in fixture.evaluations}
    assert "sympy" in adapter_ids
    assert "wolfram" in adapter_ids


def test_cross_adapter_evaluations_preserve_adapter_assignment(tmp_path: Path):
    path = _write(tmp_path, "cross.toml", _CROSS_ADAPTER_TOML)
    fixture = load_differential_fixture(path)
    by_id = {e.id: e for e in fixture.evaluations}
    assert by_id["sympy-eval"].adapter == "sympy"
    assert by_id["wolfram-eval"].adapter == "wolfram"


# --- Validation ---


def test_missing_meta_raises_schema_error(tmp_path: Path):
    path = _write(tmp_path, "bad.toml", _MISSING_META_TOML)
    with pytest.raises(SchemaError, match=r"(?i)meta"):
        load_differential_fixture(path)


def test_single_evaluation_raises_schema_error(tmp_path: Path):
    path = _write(tmp_path, "bad.toml", _SINGLE_EVAL_TOML)
    with pytest.raises(SchemaError, match=r"(?i)(evaluation|at least)"):
        load_differential_fixture(path)


def test_missing_relation_raises_schema_error(tmp_path: Path):
    path = _write(tmp_path, "bad.toml", _MISSING_RELATION_TOML)
    with pytest.raises(SchemaError, match=r"(?i)relation"):
        load_differential_fixture(path)
