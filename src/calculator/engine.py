"""Expression engine: shunting-yard parser and RPN evaluator.

The engine never calls :func:`eval`.  An expression travels through three
stages:

1. :func:`calculator.tokens.tokenize` turns text into tokens.
2. :func:`to_rpn` reorders those tokens into Reverse Polish Notation using
   Dijkstra's shunting-yard algorithm.
3. :func:`evaluate_rpn` walks the RPN stream with an operand stack.

Every failure mode raises :class:`~calculator.tokens.ParseError` or
:class:`~calculator.tokens.MathError`, both of which derive from
:class:`~calculator.tokens.CalculatorError`.
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Callable, Dict, List, Sequence

from .tokens import (
    BINARY_OPERATORS,
    FUNCTION_NAMES,
    UNARY_PRECEDENCE,
    Associativity,
    CalculatorError,
    MathError,
    ParseError,
    Token,
    TokenType,
    tokenize,
)

__all__ = [
    "AngleMode",
    "CalculatorError",
    "ParseError",
    "MathError",
    "evaluate",
    "evaluate_rpn",
    "format_result",
    "insert_implicit_multiplication",
    "to_rpn",
]

#: Results whose absolute value is below this are treated as exactly zero.  It
#: keeps ``cos(90)`` in degree mode from reading ``6.12e-17``.
_ZERO_SNAP = 1e-12


class AngleMode(str, Enum):
    """Whether trigonometric functions work in degrees or radians."""

    DEGREES = "deg"
    RADIANS = "rad"

    @property
    def label(self) -> str:
        """Human readable name, e.g. ``"Degrees"``."""
        return "Degrees" if self is AngleMode.DEGREES else "Radians"

    @classmethod
    def parse(cls, raw: str) -> AngleMode:
        """Build a mode from a string such as ``"DEG"``; defaults to radians."""
        normalised = (raw or "").strip().lower()
        for mode in cls:
            if normalised.startswith(mode.value):
                return mode
        return cls.RADIANS


def _to_radians(value: float, mode: AngleMode) -> float:
    return math.radians(value) if mode is AngleMode.DEGREES else value


def _from_radians(value: float, mode: AngleMode) -> float:
    return math.degrees(value) if mode is AngleMode.DEGREES else value


def _sin(value: float, mode: AngleMode) -> float:
    return math.sin(_to_radians(value, mode))


def _cos(value: float, mode: AngleMode) -> float:
    return math.cos(_to_radians(value, mode))


def _tan(value: float, mode: AngleMode) -> float:
    radians = _to_radians(value, mode)
    result = math.tan(radians)
    # cos() never returns exactly 0 for the float nearest pi/2, so test the
    # cosine instead of the tangent to catch the asymptote reliably.
    if abs(math.cos(radians)) < _ZERO_SNAP:
        raise MathError("tan is undefined at this angle")
    return result


def _asin(value: float, mode: AngleMode) -> float:
    if not -1.0 <= value <= 1.0:
        raise MathError("asin only accepts values between -1 and 1")
    return _from_radians(math.asin(value), mode)


def _acos(value: float, mode: AngleMode) -> float:
    if not -1.0 <= value <= 1.0:
        raise MathError("acos only accepts values between -1 and 1")
    return _from_radians(math.acos(value), mode)


def _atan(value: float, mode: AngleMode) -> float:
    return _from_radians(math.atan(value), mode)


def _log10(value: float, mode: AngleMode) -> float:
    if value <= 0.0:
        raise MathError("log is only defined for positive numbers")
    return math.log10(value)


def _ln(value: float, mode: AngleMode) -> float:
    if value <= 0.0:
        raise MathError("ln is only defined for positive numbers")
    return math.log(value)


def _sqrt(value: float, mode: AngleMode) -> float:
    if value < 0.0:
        raise MathError("sqrt is not defined for negative numbers")
    return math.sqrt(value)


def _exp(value: float, mode: AngleMode) -> float:
    try:
        return math.exp(value)
    except OverflowError as exc:
        raise MathError("The result is too large to represent") from exc


def _abs(value: float, mode: AngleMode) -> float:
    return abs(value)


def _floor(value: float, mode: AngleMode) -> float:
    return float(math.floor(value))


def _ceil(value: float, mode: AngleMode) -> float:
    return float(math.ceil(value))


#: Function implementations.  Each takes the argument and the active angle mode.
FUNCTIONS: Dict[str, Callable[[float, AngleMode], float]] = {
    "sin": _sin,
    "cos": _cos,
    "tan": _tan,
    "asin": _asin,
    "acos": _acos,
    "atan": _atan,
    "log": _log10,
    "ln": _ln,
    "sqrt": _sqrt,
    "exp": _exp,
    "abs": _abs,
    "floor": _floor,
    "ceil": _ceil,
}

if set(FUNCTIONS) != set(FUNCTION_NAMES):  # pragma: no cover - import-time guard
    missing = sorted(set(FUNCTION_NAMES) ^ set(FUNCTIONS))
    raise RuntimeError(f"Function table is out of sync with the tokenizer: {missing}")

#: Largest factorial input; 170! is the biggest that fits in a float.
_MAX_FACTORIAL = 170


def _factorial(value: float) -> float:
    """Return ``value!`` for a non-negative whole number."""
    if value < 0.0:
        raise MathError("Factorial is not defined for negative numbers")
    rounded = round(value)
    if abs(value - rounded) > 1e-9:
        raise MathError("Factorial needs a whole number")
    if rounded > _MAX_FACTORIAL:
        raise MathError(f"Factorial is only supported up to {_MAX_FACTORIAL}!")
    return float(math.factorial(int(rounded)))


_VALUE_TOKENS = {TokenType.NUMBER, TokenType.CONSTANT}
_CLOSERS = _VALUE_TOKENS | {TokenType.RPAREN, TokenType.FACTORIAL}
_OPENERS = _VALUE_TOKENS | {TokenType.FUNCTION, TokenType.LPAREN}


def insert_implicit_multiplication(tokens: Sequence[Token]) -> List[Token]:
    """Insert ``*`` where multiplication is implied.

    ``2pi``, ``3(4+1)`` and ``(1+2)(3+4)`` all become explicit products.  The
    inserted tokens carry the position of the token that follows them so that
    error messages still point at something the user typed.
    """
    result: List[Token] = []
    for token in tokens:
        if result and result[-1].type in _CLOSERS and token.type in _OPENERS:
            result.append(Token(TokenType.OPERATOR, "*", token.position))
        result.append(token)
    return result


def _pops_before(pending: Token, top: Token) -> bool:
    """Decide whether ``top`` leaves the operator stack before ``pending`` joins it."""
    if top.type is TokenType.FUNCTION:
        return True
    if top.type is TokenType.UNARY:
        return UNARY_PRECEDENCE > _precedence(pending)
    if top.type is not TokenType.OPERATOR:
        return False
    top_info = BINARY_OPERATORS[top.text]
    pending_precedence = _precedence(pending)
    if top_info.precedence > pending_precedence:
        return True
    return (
        top_info.precedence == pending_precedence
        and BINARY_OPERATORS[pending.text].associativity is Associativity.LEFT
    )


def _precedence(token: Token) -> int:
    if token.type is TokenType.UNARY:
        return UNARY_PRECEDENCE
    return BINARY_OPERATORS[token.text].precedence


def to_rpn(tokens: Sequence[Token]) -> List[Token]:
    """Reorder infix ``tokens`` into Reverse Polish Notation.

    Args:
        tokens: Tokens in source order, ideally after
            :func:`insert_implicit_multiplication`.

    Returns:
        The same operands in order, with operators moved after their operands.

    Raises:
        ParseError: On unbalanced parentheses or a function that is not
            followed by ``(``.
    """
    output: List[Token] = []
    stack: List[Token] = []
    previous: Token | None = None

    for token in tokens:
        if token.type in _VALUE_TOKENS:
            output.append(token)

        elif token.type is TokenType.FUNCTION:
            stack.append(token)

        elif token.type is TokenType.FACTORIAL:
            if previous is None or previous.type not in _CLOSERS:
                raise ParseError("'!' must follow a value", token.position)
            output.append(token)

        elif token.type is TokenType.OPERATOR:
            is_prefix = previous is None or previous.type in {
                TokenType.OPERATOR,
                TokenType.UNARY,
                TokenType.LPAREN,
                TokenType.FUNCTION,
            }
            if is_prefix:
                if token.text not in {"+", "-"}:
                    raise ParseError(f"'{token.text}' needs a value on its left", token.position)
                # A prefix operator binds to whatever comes next, so nothing is
                # popped when it is pushed.
                stack.append(Token(TokenType.UNARY, f"u{token.text}", token.position))
            else:
                while stack and _pops_before(token, stack[-1]):
                    output.append(stack.pop())
                stack.append(token)

        elif token.type is TokenType.LPAREN:
            if previous is not None and previous.type is TokenType.FUNCTION:
                pass  # The function token is already waiting on the stack.
            stack.append(token)

        elif token.type is TokenType.RPAREN:
            while stack and stack[-1].type is not TokenType.LPAREN:
                output.append(stack.pop())
            if not stack:
                raise ParseError("Unbalanced parentheses: unexpected ')'", token.position)
            stack.pop()
            if stack and stack[-1].type is TokenType.FUNCTION:
                output.append(stack.pop())

        previous = token

    for token in reversed(stack):
        if token.type is TokenType.LPAREN:
            raise ParseError("Unbalanced parentheses: a ')' is missing", token.position)
        if token.type is TokenType.FUNCTION:
            raise ParseError(f"'{token.text}' must be followed by '('", token.position)
        output.append(token)

    stack.clear()
    return output


def evaluate_rpn(rpn: Sequence[Token], angle_mode: AngleMode = AngleMode.RADIANS) -> float:
    """Evaluate a Reverse Polish Notation token stream.

    Args:
        rpn: Output of :func:`to_rpn`.
        angle_mode: Angle unit used by the trigonometric functions.

    Returns:
        The numeric result.

    Raises:
        ParseError: If the stream is incomplete or has leftover operands.
        MathError: If the arithmetic is undefined or overflows.
    """
    stack: List[float] = []

    for token in rpn:
        if token.type in _VALUE_TOKENS:
            assert token.value is not None  # guaranteed by the tokenizer
            stack.append(token.value)

        elif token.type is TokenType.OPERATOR:
            if len(stack) < 2:
                raise ParseError(f"'{token.text}' is missing a value", token.position)
            right = stack.pop()
            left = stack.pop()
            stack.append(BINARY_OPERATORS[token.text].apply(left, right))

        elif token.type is TokenType.UNARY:
            if not stack:
                raise ParseError(f"'{token.text[1]}' is missing a value", token.position)
            operand = stack.pop()
            stack.append(-operand if token.text == "u-" else operand)

        elif token.type is TokenType.FUNCTION:
            if not stack:
                raise ParseError(f"'{token.text}' needs an argument", token.position)
            stack.append(FUNCTIONS[token.text](stack.pop(), angle_mode))

        elif token.type is TokenType.FACTORIAL:
            if not stack:
                raise ParseError("'!' is missing a value", token.position)
            stack.append(_factorial(stack.pop()))

        else:  # pragma: no cover - parentheses never reach the evaluator
            raise ParseError(f"Unexpected token '{token.text}'", token.position)

    if not stack:
        raise ParseError("The expression is empty")
    if len(stack) > 1:
        raise ParseError("The expression has values that are not joined by an operator")

    result = stack[0]
    if math.isnan(result):
        raise MathError("The result is not a number")
    if math.isinf(result):
        raise MathError("The result is infinite")
    if abs(result) < _ZERO_SNAP:
        return 0.0
    return result


def evaluate(expression: str, angle_mode: AngleMode = AngleMode.RADIANS) -> float:
    """Evaluate an infix expression.

    Args:
        expression: Text such as ``"2 + 3 * sin(pi / 2)"``.
        angle_mode: Angle unit used by the trigonometric functions.

    Returns:
        The numeric result.

    Raises:
        ParseError: If the expression is malformed.
        MathError: If the arithmetic is undefined.
    """
    if expression is None or not expression.strip():
        raise ParseError("The expression is empty")
    tokens = insert_implicit_multiplication(tokenize(expression))
    return evaluate_rpn(to_rpn(tokens), angle_mode)


def format_result(value: float, precision: int = 12) -> str:
    """Render ``value`` the way the display should show it.

    Whole numbers lose their ``.0``, long decimals are trimmed, and very large
    or very small magnitudes switch to scientific notation.
    """
    if value == 0.0:
        return "0"
    magnitude = abs(value)
    if magnitude >= 1e12 or magnitude < 1e-9:
        mantissa, exponent = f"{value:.{max(precision - 6, 1)}e}".split("e")
        if "." in mantissa:
            mantissa = mantissa.rstrip("0").rstrip(".")
        sign = exponent[0]
        digits = exponent[1:].lstrip("0") or "0"
        return f"{mantissa}e{sign}{digits}"
    text = f"{value:.{precision}g}"
    if "e" in text or "E" in text:  # pragma: no cover - range handled above
        return text
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
