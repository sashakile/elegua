"""Tests for ExecutionContext — variable store for store_as chaining."""

from __future__ import annotations

from elegua.context import ExecutionContext

# --- store / resolve ---


def test_store_and_resolve():
    ctx = ExecutionContext()
    ctx.store("x", "hello")
    assert ctx.resolve("x") == "hello"


def test_resolve_unknown_returns_none():
    ctx = ExecutionContext()
    assert ctx.resolve("missing") is None


def test_store_overwrites():
    ctx = ExecutionContext()
    ctx.store("x", "first")
    ctx.store("x", "second")
    assert ctx.resolve("x") == "second"


# --- resolve_refs in payload ---


def test_resolve_refs_substitutes_string():
    ctx = ExecutionContext()
    ctx.store("diff", "T[-a,-b] - T[-b,-a]")
    result = ctx.resolve_refs({"expression": "$diff"})
    assert result == {"expression": "T[-a,-b] - T[-b,-a]"}


def test_resolve_refs_leaves_non_strings():
    ctx = ExecutionContext()
    ctx.store("x", "42")
    result = ctx.resolve_refs({"count": 5, "items": ["a", "b"], "flag": True})
    assert result == {"count": 5, "items": ["a", "b"], "flag": True}


def test_resolve_refs_unknown_ref_preserved():
    ctx = ExecutionContext()
    result = ctx.resolve_refs({"expression": "$unknown"})
    assert result == {"expression": "$unknown"}


def test_resolve_refs_multiple_refs_in_one_string():
    ctx = ExecutionContext()
    ctx.store("a", "X")
    ctx.store("b", "Y")
    result = ctx.resolve_refs({"expr": "$a + $b"})
    assert result == {"expr": "X + Y"}


def test_resolve_refs_does_not_mutate_input():
    ctx = ExecutionContext()
    ctx.store("x", "val")
    original = {"expr": "$x"}
    ctx.resolve_refs(original)
    assert original == {"expr": "$x"}


def test_resolve_refs_empty_payload():
    ctx = ExecutionContext()
    assert ctx.resolve_refs({}) == {}


def test_resolve_refs_no_dollar_sign_untouched():
    ctx = ExecutionContext()
    result = ctx.resolve_refs({"expr": "plain text"})
    assert result == {"expr": "plain text"}


# --- snapshot / restore (scope management) ---


def test_snapshot_captures_current_state():
    ctx = ExecutionContext()
    ctx.store("setup_var", "manifold_M")
    snap = ctx.snapshot()
    assert snap == {"setup_var": "manifold_M"}


def test_snapshot_is_independent_copy():
    ctx = ExecutionContext()
    ctx.store("x", "1")
    snap = ctx.snapshot()
    ctx.store("y", "2")
    assert "y" not in snap


def test_restore_resets_to_snapshot():
    ctx = ExecutionContext()
    ctx.store("setup", "M")
    snap = ctx.snapshot()
    # Simulate test-local bindings
    ctx.store("local", "T[-a,-b]")
    assert ctx.resolve("local") == "T[-a,-b]"
    # Restore to setup state
    ctx.restore(snap)
    assert ctx.resolve("local") is None
    assert ctx.resolve("setup") == "M"


def test_scoping_pattern_setup_then_tests():
    """Full sxAct scoping pattern: setup bindings shared, test bindings isolated."""
    ctx = ExecutionContext()

    # Setup phase
    ctx.store("M", "manifold_4d")
    ctx.store("T", "tensor_sym")
    setup_snap = ctx.snapshot()

    # Test 1: adds local binding
    ctx.store("diff", "T[-a,-b] - T[-b,-a]")
    resolved = ctx.resolve_refs({"expression": "$diff"})
    assert resolved["expression"] == "T[-a,-b] - T[-b,-a]"
    assert ctx.resolve("M") == "manifold_4d"  # setup still visible
    ctx.restore(setup_snap)

    # Test 2: local binding from test 1 is gone
    assert ctx.resolve("diff") is None
    assert ctx.resolve("M") == "manifold_4d"  # setup still there


# --- contains ---


def test_contains():
    ctx = ExecutionContext()
    assert "x" not in ctx
    ctx.store("x", "val")
    assert "x" in ctx
