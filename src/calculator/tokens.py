"""Lexical layer for the calculator: token types, operator tables and the tokenizer.

This module is deliberately free of any evaluation logic.  It knows how to turn
a piece of text into a flat list of :class:`Token` objects and which symbols are
legal, but it never computes a result.  Evaluation lives in
:mod:`calculator.engine`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Dict, FrozenSet, List, NamedTuple, Optional

__all__ = [
    "CalculatorError",
    "ParseError",
    "MathError",
    "TokenType",
    "Token",
    "Associativity",
    "OperatorInfo",
    "BINARY_OPERATORS",
    "CONSTANTS",
    "FUNCTION_NAMES",
    "tokenize",
]


class CalculatorError(Exception):
    """Base class for every error the calculator raises on purpose.

    The GUI catches this class (and nothing broader) so that genuine bugs keep
    producing tracebacks instead of being swallowed as "user error".
    """

    def __init__(self, message: str, position: Optional[int] = None) -> None:
        super().__init__(message)
        self.message = message
        self.position = position

    def __str__(self) -> str:  # pragma: no cover - trivial formatting
        if self.position is None:
            return self.message
        return f"{self.message} (at character {self.position + 1})"


class ParseError(CalculatorError):
    """The expression is not well formed: bad character, bad structure."""


class MathError(CalculatorError):
    """The expression parsed, but the arithmetic is undefined or unrepresentable."""


class TokenType(Enum):
    """The kinds of token produced by :func:`tokenize`."""

    NUMBER = auto()
    CONSTANT = auto()
    FUNCTION = auto()
    OPERATOR = auto()
    UNARY = auto()
    FACTORIAL = auto()
    LPAREN = auto()
    RPAREN = auto()


@dataclass(frozen=True)
class Token:
    """A single lexical unit.

    Attributes:
        type: The token category.
        text: The exact source text (or a synthesised symbol such as ``u-``).
        position: Index of the first character in the source expression.
        value: Numeric payload, set only for ``NUMBER`` and ``CONSTANT`` tokens.
    """

    type: TokenType
    text: str
    position: int
    value: Optional[float] = None


class Associativity(Enum):
    """Associativity of a binary operator."""

    LEFT = auto()
    RIGHT = auto()


def _add(left: float, right: float) -> float:
    return left + right


def _subtract(left: float, right: float) -> float:
    return left - right


def _multiply(left: float, right: float) -> float:
    return left * right


def _divide(left: float, right: float) -> float:
    if right == 0.0:
        raise MathError("Cannot divide by zero")
    return left / right


def _modulo(left: float, right: float) -> float:
    if right == 0.0:
        raise MathError("Cannot take a remainder with a divisor of zero")
    return math.fmod(left, right)


def _power(left: float, right: float) -> float:
    if left < 0.0 and not float(right).is_integer():
        raise MathError("A negative base needs a whole-number exponent")
    if left == 0.0 and right < 0.0:
        raise MathError("Zero cannot be raised to a negative power")
    try:
        return float(left**right)
    except OverflowError as exc:
        raise MathError("The result is too large to represent") from exc


class OperatorInfo(NamedTuple):
    """Precedence, associativity and implementation of a binary operator."""

    symbol: str
    precedence: int
    associativity: Associativity
    apply: Callable[[float, float], float]


#: Binary operators keyed by their source symbol.
BINARY_OPERATORS: Dict[str, OperatorInfo] = {
    "+": OperatorInfo("+", 1, Associativity.LEFT, _add),
    "-": OperatorInfo("-", 1, Associativity.LEFT, _subtract),
    "*": OperatorInfo("*", 2, Associativity.LEFT, _multiply),
    "/": OperatorInfo("/", 2, Associativity.LEFT, _divide),
    "%": OperatorInfo("%", 2, Associativity.LEFT, _modulo),
    "^": OperatorInfo("^", 4, Associativity.RIGHT, _power),
}

#: Precedence of the prefix ``+``/``-`` operators.  Lower than ``^`` so that
#: ``-2^2`` is ``-(2^2)``, higher than ``*`` so that ``-2*3`` is ``(-2)*3``.
UNARY_PRECEDENCE: int = 3

#: Named constants usable anywhere a number is allowed.
CONSTANTS: Dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}

#: Every function name the engine understands.  ``calculator.engine`` verifies
#: at import time that it provides an implementation for each of these.
FUNCTION_NAMES: FrozenSet[str] = frozenset(
    {
        "sin",
        "cos",
        "tan",
        "asin",
        "acos",
        "atan",
        "log",
        "ln",
        "sqrt",
        "exp",
        "abs",
        "floor",
        "ceil",
    }
)

#: Characters the GUI may emit that have a plain ASCII equivalent.
_CHARACTER_ALIASES: Dict[str, str] = {
    "×": "*",
    "÷": "/",
    "−": "-",
    "–": "-",
    "⁄": "/",
    "π": "pi",
    "√": "sqrt",
}

_OPERATOR_CHARACTERS = frozenset(BINARY_OPERATORS)


def _normalise(expression: str) -> str:
    """Replace typographic symbols with their ASCII equivalents."""
    if not any(char in expression for char in _CHARACTER_ALIASES):
        return expression
    return "".join(_CHARACTER_ALIASES.get(char, char) for char in expression)


def _read_number(expression: str, start: int) -> int:
    """Return the index just past the number that begins at ``start``.

    Accepts ``12``, ``12.5``, ``.5`` and ``1.2e-3``.  An ``e`` is only treated
    as an exponent marker when digits actually follow it, so ``2e`` still reads
    as ``2 * e``.
    """
    index = start
    length = len(expression)
    seen_digit = False
    seen_dot = False
    while index < length:
        char = expression[index]
        if char.isdigit():
            seen_digit = True
            index += 1
        elif char == "." and not seen_dot:
            seen_dot = True
            index += 1
        else:
            break
    if not seen_digit:
        raise ParseError(f"'{expression[start : index + 1]}' is not a valid number", start)
    if index < length and expression[index] in "eE":
        cursor = index + 1
        if cursor < length and expression[cursor] in "+-":
            cursor += 1
        if cursor < length and expression[cursor].isdigit():
            while cursor < length and expression[cursor].isdigit():
                cursor += 1
            index = cursor
    return index


def _read_identifier(expression: str, start: int) -> int:
    """Return the index just past the identifier that begins at ``start``."""
    index = start
    while index < len(expression) and (expression[index].isalpha() or expression[index] == "_"):
        index += 1
    return index


def tokenize(expression: str) -> List[Token]:
    """Split ``expression`` into tokens.

    Args:
        expression: The raw text typed by the user.

    Returns:
        The tokens in source order.

    Raises:
        ParseError: On an unknown character, malformed number, or an
            identifier that is neither a known constant nor a known function.
    """
    source = _normalise(expression)
    tokens: List[Token] = []
    index = 0
    length = len(source)

    while index < length:
        char = source[index]

        if char.isspace() or char in {",", "_"}:
            # Commas and underscores are accepted purely as digit separators.
            index += 1
            continue

        if char.isdigit() or char == ".":
            end = _read_number(source, index)
            raw = source[index:end]
            try:
                value = float(raw)
            except ValueError as exc:  # pragma: no cover - guarded by _read_number
                raise ParseError(f"'{raw}' is not a valid number", index) from exc
            tokens.append(Token(TokenType.NUMBER, raw, index, value))
            index = end
            continue

        if char.isalpha() or char == "_":
            end = _read_identifier(source, index)
            name = source[index:end].lower()
            if name in CONSTANTS:
                tokens.append(Token(TokenType.CONSTANT, name, index, CONSTANTS[name]))
            elif name in FUNCTION_NAMES:
                tokens.append(Token(TokenType.FUNCTION, name, index))
            else:
                raise ParseError(f"Unknown function or constant '{name}'", index)
            index = end
            continue

        if char in _OPERATOR_CHARACTERS:
            tokens.append(Token(TokenType.OPERATOR, char, index))
            index += 1
            continue

        if char == "!":
            tokens.append(Token(TokenType.FACTORIAL, char, index))
            index += 1
            continue

        if char in "([{":
            tokens.append(Token(TokenType.LPAREN, "(", index))
            index += 1
            continue

        if char in ")]}":
            tokens.append(Token(TokenType.RPAREN, ")", index))
            index += 1
            continue

        raise ParseError(f"Unexpected character '{char}'", index)

    return tokens
