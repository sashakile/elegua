"""Tests for SymPy expression parsing — Wolfram-first with Python fallback."""

from __future__ import annotations

import pytest

pytest.importorskip("sympy")

import sympy

from elegua.sympy.parsing import parse_expression

# --- Wolfram syntax ---


def test_parse_wolfram_trig():
    """Sin[x] + Cos[x] → sin(x) + cos(x)."""
    x = sympy.Symbol("x")
    result = parse_expression("Sin[x] + Cos[x]")
    assert result == sympy.sin(x) + sympy.cos(x)


def test_parse_wolfram_power_caret():
    """x^2 + 1 via parse_mathematica → x**2 + 1, not Xor."""
    x = sympy.Symbol("x")
    result = parse_expression("x^2 + 1")
    assert result == x**2 + 1


def test_parse_wolfram_nested():
    """Power[x, 2] → x**2."""
    x = sympy.Symbol("x")
    result = parse_expression("Power[x, 2]")
    assert result == x**2


# --- Python syntax fallback ---


def test_parse_python_syntax():
    """sin(x) + cos(x) parsed via Python fallback."""
    x = sympy.Symbol("x")
    result = parse_expression("sin(x) + cos(x)")
    assert result == sympy.sin(x) + sympy.cos(x)


def test_parse_python_double_star():
    """x**2 + 1 via Python parser."""
    x = sympy.Symbol("x")
    result = parse_expression("x**2 + 1")
    assert result == x**2 + 1


# --- Explicit parse_mode ---


def test_parse_mode_mathematica():
    """Explicit mathematica mode parses Wolfram syntax."""
    x = sympy.Symbol("x")
    result = parse_expression("Sin[x]", parse_mode="mathematica")
    assert result == sympy.sin(x)


def test_parse_mode_python():
    """Explicit python mode uses parse_expr directly."""
    x = sympy.Symbol("x")
    result = parse_expression("x**2", parse_mode="python")
    assert result == x**2


def test_parse_mode_python_caret_fails():
    """In python mode, ^ on symbols raises (no XOR support)."""
    with pytest.raises(ValueError, match=r"(?i)parse"):
        parse_expression("x^2", parse_mode="python")


# --- Error cases ---


def test_unparsable_raises():
    """Completely invalid input raises ValueError."""
    with pytest.raises(ValueError, match=r"(?i)parse"):
        parse_expression("<<<invalid>>>")


def test_unparsable_mathematica_mode():
    """Invalid input in mathematica mode raises ValueError."""
    with pytest.raises(ValueError, match=r"(?i)parse"):
        parse_expression("<<<invalid>>>", parse_mode="mathematica")


# --- Security: code injection via parse_expr (elegua-bee8) ---


def test_parse_expr_rejects_code_injection():
    """parse_expr with __import__ must raise ValueError, not execute code.

    parse_expr() uses eval() internally. Without namespace restriction,
    __import__('os').system('id') would execute a shell command.
    """
    # This should raise ValueError, NOT execute a shell command
    with pytest.raises(ValueError, match=r"(?i)parse|injection|unsafe"):
        parse_expression("__import__('os').system('id')")


def test_parse_expr_rejects_os_call():
    """os.system call via parse_expr should raise ValueError."""
    with pytest.raises(ValueError, match=r"(?i)parse|injection|unsafe"):
        parse_expression("__import__('os').popen('id')")


def test_parse_expr_rejects_builtins_access():
    """Access to __builtins__ via parse_expr should raise ValueError."""
    with pytest.raises(ValueError, match=r"(?i)parse|injection|unsafe"):
        parse_expression("__builtins__['eval']('1+1')")


def test_parse_expr_injection_raises_in_python_mode():
    """Code injection via __import__ in explicit python mode raises ValueError."""
    with pytest.raises(ValueError, match=r"(?i)parse|injection|unsafe"):
        parse_expression(
            "__import__('os').system('id')",
            parse_mode="python",
        )


def test_parse_expr_legitimate_expression_still_works():
    """Normal expressions like sin(x) + cos(x) still parse correctly."""
    x = sympy.Symbol("x")
    result = parse_expression("sin(x) + cos(x)")
    assert result == sympy.sin(x) + sympy.cos(x)


def test_parse_expr_python_mode_still_works():
    """Normal expressions in explicit python mode still parse correctly."""
    x = sympy.Symbol("x")
    result = parse_expression("x**2 + 1", parse_mode="python")
    assert result == x**2 + 1
