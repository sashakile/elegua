"""Tests for sxAct TOML format bridge loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from elegua.bridge import (
    Expected,
    Operation,
    TestFileMeta,
    load_sxact_toml,
)
from elegua.task import EleguaTask

FIXTURES = Path(__file__).parent / "fixtures"


# --- Loading: meta ---


def test_load_meta():
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    assert tf.meta.id == "bridge/basic"
    assert tf.meta.description == "Bridge loader smoke test"
    assert tf.meta.tags == ["bridge", "layer:1"]
    assert tf.meta.layer == 1
    assert tf.meta.oracle_is_axiom is True
    assert tf.meta.skip is None


def test_load_meta_defaults(tmp_path: Path):
    f = tmp_path / "minimal.toml"
    f.write_text('[meta]\nid = "x"\ndescription = "d"\n')
    tf = load_sxact_toml(f)
    assert tf.meta.tags == []
    assert tf.meta.layer == 1
    assert tf.meta.oracle_is_axiom is True


def test_load_missing_meta(tmp_path: Path):
    f = tmp_path / "bad.toml"
    f.write_text("[[setup]]\naction = 'Foo'\n")
    with pytest.raises(ValueError, match="missing required 'meta'"):
        load_sxact_toml(f)


def test_load_meta_missing_id(tmp_path: Path):
    f = tmp_path / "bad.toml"
    f.write_text('[meta]\ndescription = "d"\n')
    with pytest.raises(ValueError, match="meta missing required 'id'"):
        load_sxact_toml(f)


def test_load_meta_missing_description(tmp_path: Path):
    f = tmp_path / "bad.toml"
    f.write_text('[meta]\nid = "x"\n')
    with pytest.raises(ValueError, match="meta missing required 'description'"):
        load_sxact_toml(f)


# --- Loading: setup ---


def test_load_setup_operations():
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    assert len(tf.setup) == 2
    assert tf.setup[0].action == "DefManifold"
    assert tf.setup[0].store_as == "M"
    assert tf.setup[0].args["name"] == "M"
    assert tf.setup[0].args["dimension"] == 4
    assert tf.setup[1].action == "DefTensor"
    assert tf.setup[1].store_as == "T"


def test_load_empty_setup(tmp_path: Path):
    f = tmp_path / "no_setup.toml"
    f.write_text('[meta]\nid = "x"\ndescription = "d"\n')
    tf = load_sxact_toml(f)
    assert tf.setup == []


def test_setup_operation_missing_action(tmp_path: Path):
    f = tmp_path / "bad.toml"
    f.write_text('[meta]\nid = "x"\ndescription = "d"\n\n[[setup]]\nstore_as = "X"\n')
    with pytest.raises(ValueError, match="operation missing required 'action'"):
        load_sxact_toml(f)


def test_setup_operation_no_args(tmp_path: Path):
    f = tmp_path / "no_args.toml"
    f.write_text('[meta]\nid = "x"\ndescription = "d"\n\n[[setup]]\naction = "Foo"\n')
    tf = load_sxact_toml(f)
    assert tf.setup[0].args == {}
    assert tf.setup[0].store_as is None


# --- Loading: tests ---


def test_load_test_cases():
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    assert len(tf.tests) == 2
    t0 = tf.tests[0]
    assert t0.id == "canon_symmetric"
    assert t0.description == "Symmetric swap canonicalizes to zero"
    assert len(t0.operations) == 3
    assert t0.operations[0].action == "Evaluate"
    assert t0.operations[0].store_as == "diff"
    assert t0.operations[1].action == "ToCanonical"
    assert t0.operations[2].action == "Assert"
    assert t0.operations[2].store_as is None


def test_load_test_dependencies():
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    assert tf.tests[0].dependencies == []
    assert tf.tests[1].dependencies == ["canon_symmetric"]


def test_load_test_expected():
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    exp = tf.tests[0].expected
    assert exp is not None
    assert exp.is_zero is True
    assert exp.comparison_tier == 1
    assert exp.expr is None


def test_load_test_no_expected():
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    assert tf.tests[1].expected is None


def test_load_test_missing_id(tmp_path: Path):
    f = tmp_path / "bad.toml"
    f.write_text(
        '[meta]\nid = "x"\ndescription = "d"\n\n'
        '[[tests]]\ndescription = "d"\n\n'
        "[[tests.operations]]\naction = 'Foo'\n"
    )
    with pytest.raises(ValueError, match="tests\\[0\\] missing required 'id'"):
        load_sxact_toml(f)


def test_load_test_missing_description(tmp_path: Path):
    f = tmp_path / "bad.toml"
    f.write_text(
        '[meta]\nid = "x"\ndescription = "d"\n\n'
        '[[tests]]\nid = "t1"\n\n'
        "[[tests.operations]]\naction = 'Foo'\n"
    )
    with pytest.raises(ValueError, match="tests\\[0\\] missing required 'description'"):
        load_sxact_toml(f)


def test_load_test_no_operations(tmp_path: Path):
    f = tmp_path / "bad.toml"
    f.write_text('[meta]\nid = "x"\ndescription = "d"\n\n[[tests]]\nid = "t1"\ndescription = "d"\n')
    with pytest.raises(ValueError, match="tests\\[0\\] must have at least one operation"):
        load_sxact_toml(f)


def test_load_empty_tests(tmp_path: Path):
    f = tmp_path / "no_tests.toml"
    f.write_text('[meta]\nid = "x"\ndescription = "d"\n')
    tf = load_sxact_toml(f)
    assert tf.tests == []


# --- Loading: expected fields ---


def test_expected_all_fields(tmp_path: Path):
    f = tmp_path / "full_expected.toml"
    f.write_text(
        '[meta]\nid = "x"\ndescription = "d"\n\n'
        '[[tests]]\nid = "t1"\ndescription = "d"\n\n'
        "[[tests.operations]]\naction = 'Eval'\n\n"
        "[tests.expected]\n"
        'expr = "T[-a,-b]"\n'
        'normalized = "$1 $2"\n'
        "value = 42\n"
        "is_zero = false\n"
        "comparison_tier = 2\n"
        "expect_error = false\n\n"
        "[tests.expected.properties]\n"
        "rank = 2\n"
        'type = "Tensor"\n'
    )
    tf = load_sxact_toml(f)
    exp = tf.tests[0].expected
    assert exp is not None
    assert exp.expr == "T[-a,-b]"
    assert exp.normalized == "$1 $2"
    assert exp.value == 42
    assert exp.is_zero is False
    assert exp.comparison_tier == 2
    assert exp.expect_error is False
    assert exp.properties == {"rank": 2, "type": "Tensor"}


# --- Conversion to EleguaTask ---


def test_to_tasks_includes_setup_and_tests():
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    tasks = tf.to_tasks()
    assert all(isinstance(t, EleguaTask) for t in tasks)
    # 2 setup + 3 ops in test 0 + 1 op in test 1 = 6
    assert len(tasks) == 6


def test_to_tasks_setup_first():
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    tasks = tf.to_tasks()
    assert tasks[0].action == "DefManifold"
    assert tasks[1].action == "DefTensor"
    assert tasks[2].action == "Evaluate"


def test_to_tasks_preserves_args_in_payload():
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    tasks = tf.to_tasks()
    assert tasks[0].payload["name"] == "M"
    assert tasks[0].payload["dimension"] == 4


def test_to_tasks_preserves_store_as():
    tf = load_sxact_toml(FIXTURES / "sxact_basic.toml")
    tasks = tf.to_tasks()
    assert tasks[0].payload["_store_as"] == "M"
    assert tasks[1].payload["_store_as"] == "T"
    # Assert operation has no store_as
    assert "_store_as" not in tasks[5].payload


def test_to_tasks_empty_file(tmp_path: Path):
    f = tmp_path / "empty.toml"
    f.write_text('[meta]\nid = "x"\ndescription = "d"\n')
    tf = load_sxact_toml(f)
    assert tf.to_tasks() == []


# --- Data model invariants ---


def test_test_file_meta_is_frozen():
    meta = TestFileMeta(id="x", description="d")
    with pytest.raises(AttributeError):
        meta.id = "y"  # type: ignore[misc]


def test_operation_is_frozen():
    op = Operation(action="Foo")
    with pytest.raises(AttributeError):
        op.action = "Bar"  # type: ignore[misc]


def test_expected_is_frozen():
    exp = Expected(is_zero=True)
    with pytest.raises(AttributeError):
        exp.is_zero = False  # type: ignore[misc]
