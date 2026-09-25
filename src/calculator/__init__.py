"""PyCalculator: a standalone desktop calculator with a Tkinter interface.

The public surface is intentionally small::

    from calculator import evaluate, AngleMode

    evaluate("sin(30) + 2^3", AngleMode.DEGREES)

Importing this package does not import :mod:`tkinter`; the GUI lives in
:mod:`calculator.app` and is only pulled in when you ask for it.
"""

from __future__ import annotations

from .engine import AngleMode, evaluate, evaluate_rpn, format_result, to_rpn
from .tokens import CalculatorError, MathError, ParseError, Token, TokenType, tokenize

__all__ = [
    "AngleMode",
    "CalculatorError",
    "MathError",
    "ParseError",
    "Token",
    "TokenType",
    "evaluate",
    "evaluate_rpn",
    "format_result",
    "to_rpn",
    "tokenize",
    "__version__",
]

__version__ = "1.0.0"
