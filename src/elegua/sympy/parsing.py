"""Expression parsing for the SymPy adapter.

Two-parser chain: parse_mathematica() first (Wolfram syntax like Sin[x],
x^2), falling back to parse_expr() (Python syntax like sin(x), x**2).
Configurable via parse_mode parameter.
"""

from __future__ import annotations

from typing import Literal

import sympy
from sympy.parsing.mathematica import parse_mathematica
from sympy.parsing.sympy_parser import parse_expr


def parse_expression(
    text: str,
    parse_mode: Literal["auto", "mathematica", "python"] = "auto",
) -> sympy.Expr:
    """Parse an expression string into a SymPy expression.

    Parameters:
        text: Expression string in Wolfram or Python syntax.
        parse_mode: Parser selection — 'auto' tries Wolfram first then
            Python, 'mathematica' uses only parse_mathematica(),
            'python' uses only parse_expr().

    Returns:
        A SymPy expression.

    Raises:
        ValueError: If the expression cannot be parsed.
    """
    if parse_mode == "mathematica":
        return _parse_mathematica(text)
    if parse_mode == "python":
        return _parse_python(text)

    # Auto mode: try Wolfram first, fall back to Python
    try:
        return _parse_mathematica(text)
    except Exception:
        pass

    try:
        return _parse_python(text)
    except Exception:
        pass

    msg = f"Failed to parse expression: {text!r}"
    raise ValueError(msg)


def _parse_mathematica(text: str) -> sympy.Expr:
    """Parse Wolfram/Mathematica syntax."""
    try:
        result = parse_mathematica(text)
    except Exception as exc:
        msg = f"Mathematica parse failed for {text!r}: {exc}"
        raise ValueError(msg) from exc
    if result is None:
        msg = f"Mathematica parse returned None for {text!r}"
        raise ValueError(msg)
    return result


def _parse_python(text: str) -> sympy.Expr:
    """Parse Python/SymPy syntax."""
    try:
        result = parse_expr(text)
    except Exception as exc:
        msg = f"Python parse failed for {text!r}: {exc}"
        raise ValueError(msg) from exc
    if result is None:
        msg = f"Python parse returned None for {text!r}"
        raise ValueError(msg)
    return result
