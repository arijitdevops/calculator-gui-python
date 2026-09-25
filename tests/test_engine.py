"""Tests for the tokenizer, the shunting-yard parser and the RPN evaluator."""

from __future__ import annotations

import math

import pytest

from calculator.engine import (
    AngleMode,
    evaluate,
    format_result,
    insert_implicit_multiplication,
    to_rpn,
)
from calculator.tokens import CalculatorError, MathError, ParseError, TokenType, tokenize


def rpn_text(expression: str) -> str:
    """Return the RPN form of ``expression`` as a space separated string."""
    tokens = insert_implicit_multiplication(tokenize(expression))
    return " ".join(token.text for token in to_rpn(tokens))


class TestTokenizer:
    def test_numbers_and_operators(self) -> None:
        tokens = tokenize("12.5 + 3")
        assert [token.type for token in tokens] == [
            TokenType.NUMBER,
            TokenType.OPERATOR,
            TokenType.NUMBER,
        ]
        assert tokens[0].value == pytest.approx(12.5)

    def test_scientific_notation(self) -> None:
        assert evaluate("1.5e3") == pytest.approx(1500.0)
        assert evaluate("2e-3") == pytest.approx(0.002)

    def test_bare_e_is_the_constant(self) -> None:
        assert evaluate("e") == pytest.approx(math.e)
        assert evaluate("2e") == pytest.approx(2 * math.e)

    def test_unicode_aliases(self) -> None:
        assert evaluate("6 ÷ 3") == pytest.approx(2.0)
        assert evaluate("6 × 3") == pytest.approx(18.0)
        assert evaluate("π") == pytest.approx(math.pi)

    def test_unknown_character_raises(self) -> None:
        with pytest.raises(ParseError, match="Unexpected character"):
            tokenize("2 @ 3")

    def test_unknown_identifier_raises(self) -> None:
        with pytest.raises(ParseError, match="Unknown function or constant"):
            tokenize("frobnicate(2)")

    def test_error_carries_a_position(self) -> None:
        with pytest.raises(ParseError) as info:
            tokenize("1 + @")
        assert info.value.position == 4


class TestPrecedenceAndAssociativity:
    @pytest.mark.parametrize(
        ("expression", "expected"),
        [
            ("2 + 3 * 4", 14.0),
            ("(2 + 3) * 4", 20.0),
            ("2 * 3 + 4 * 5", 26.0),
            ("100 / 10 / 2", 5.0),
            ("1 - 2 - 3", -4.0),
            ("10 % 3", 1.0),
            ("2 + 10 % 3", 3.0),
        ],
    )
    def test_binary_precedence(self, expression: str, expected: float) -> None:
        assert evaluate(expression) == pytest.approx(expected)

    def test_power_is_right_associative(self) -> None:
        assert evaluate("2 ^ 3 ^ 2") == pytest.approx(512.0)
        assert rpn_text("2 ^ 3 ^ 2") == "2 3 2 ^ ^"

    def test_subtraction_is_left_associative(self) -> None:
        assert rpn_text("1 - 2 - 3") == "1 2 - 3 -"

    def test_parentheses_override_precedence(self) -> None:
        assert evaluate("(2 ^ 3) ^ 2") == pytest.approx(64.0)


class TestUnaryMinus:
    def test_leading_minus(self) -> None:
        assert evaluate("-5") == pytest.approx(-5.0)

    def test_binds_looser_than_power(self) -> None:
        assert evaluate("-2 ^ 2") == pytest.approx(-4.0)
        assert rpn_text("-2 ^ 2") == "2 2 ^ u-"

    def test_binds_tighter_than_multiplication(self) -> None:
        assert evaluate("-2 * 3") == pytest.approx(-6.0)
        assert rpn_text("-2 * 3") == "2 u- 3 *"

    def test_after_an_operator(self) -> None:
        assert evaluate("2 ^ -2") == pytest.approx(0.25)
        assert evaluate("5 * -3") == pytest.approx(-15.0)
        assert evaluate("5 - -3") == pytest.approx(8.0)

    def test_stacked_unary_operators(self) -> None:
        assert evaluate("--5") == pytest.approx(5.0)
        assert evaluate("-+-5") == pytest.approx(5.0)

    def test_unary_inside_parentheses(self) -> None:
        assert evaluate("3 * (-2 + 5)") == pytest.approx(9.0)

    def test_binary_operator_without_a_left_operand(self) -> None:
        with pytest.raises(ParseError, match="needs a value on its left"):
            evaluate("* 3")


class TestFunctions:
    def test_basic_functions(self) -> None:
        assert evaluate("sqrt(16)") == pytest.approx(4.0)
        assert evaluate("abs(-7)") == pytest.approx(7.0)
        assert evaluate("floor(2.7)") == pytest.approx(2.0)
        assert evaluate("ceil(2.1)") == pytest.approx(3.0)
        assert evaluate("exp(0)") == pytest.approx(1.0)

    def test_logarithms(self) -> None:
        assert evaluate("log(1000)") == pytest.approx(3.0)
        assert evaluate("ln(e)") == pytest.approx(1.0)

    def test_nested_functions(self) -> None:
        assert evaluate("sqrt(sqrt(16))") == pytest.approx(2.0)
        assert evaluate("abs(floor(-2.5))") == pytest.approx(3.0)
        assert evaluate("sqrt(abs(-9)) + ln(exp(2))") == pytest.approx(5.0)

    def test_function_of_an_expression(self) -> None:
        assert evaluate("sqrt(3 * 3 + 4 * 4)") == pytest.approx(5.0)

    def test_function_must_be_called(self) -> None:
        with pytest.raises(ParseError, match="must be followed by"):
            evaluate("sqrt")

    def test_function_needs_an_argument(self) -> None:
        with pytest.raises(ParseError):
            evaluate("sqrt()")


class TestAngleModes:
    def test_radians_is_the_default(self) -> None:
        assert evaluate("sin(pi / 2)") == pytest.approx(1.0)

    def test_degrees(self) -> None:
        assert evaluate("sin(30)", AngleMode.DEGREES) == pytest.approx(0.5)
        assert evaluate("cos(90)", AngleMode.DEGREES) == pytest.approx(0.0)

    def test_inverse_functions_return_the_active_unit(self) -> None:
        assert evaluate("asin(1)", AngleMode.DEGREES) == pytest.approx(90.0)
        assert evaluate("atan(1)", AngleMode.RADIANS) == pytest.approx(math.pi / 4)

    def test_tan_asymptote_is_reported(self) -> None:
        with pytest.raises(MathError, match="tan is undefined"):
            evaluate("tan(90)", AngleMode.DEGREES)

    def test_mode_parsing(self) -> None:
        assert AngleMode.parse("DEG") is AngleMode.DEGREES
        assert AngleMode.parse("degrees") is AngleMode.DEGREES
        assert AngleMode.parse("") is AngleMode.RADIANS
        assert AngleMode.parse("nonsense") is AngleMode.RADIANS


class TestFactorial:
    @pytest.mark.parametrize(
        ("expression", "expected"), [("0!", 1.0), ("5!", 120.0), ("10!", 3628800.0)]
    )
    def test_values(self, expression: str, expected: float) -> None:
        assert evaluate(expression) == pytest.approx(expected)

    def test_applies_to_a_parenthesised_group(self) -> None:
        assert evaluate("(2 + 1)!") == pytest.approx(6.0)

    def test_binds_tighter_than_multiplication(self) -> None:
        assert evaluate("2 * 3!") == pytest.approx(12.0)
        assert evaluate("3! + 1") == pytest.approx(7.0)

    def test_negative_input(self) -> None:
        with pytest.raises(MathError, match="negative"):
            evaluate("(-3)!")

    def test_fractional_input(self) -> None:
        with pytest.raises(MathError, match="whole number"):
            evaluate("2.5!")

    def test_too_large(self) -> None:
        with pytest.raises(MathError, match="only supported up to"):
            evaluate("200!")

    def test_needs_a_left_operand(self) -> None:
        with pytest.raises(ParseError, match="must follow a value"):
            evaluate("!5")


class TestImplicitMultiplication:
    @pytest.mark.parametrize(
        ("expression", "expected"),
        [
            ("2pi", 2 * math.pi),
            ("3(4 + 1)", 15.0),
            ("(1 + 1)(2 + 2)", 8.0),
            ("2sqrt(9)", 6.0),
        ],
    )
    def test_products_are_inferred(self, expression: str, expected: float) -> None:
        assert evaluate(expression) == pytest.approx(expected)

    def test_inserted_token_is_a_multiplication(self) -> None:
        tokens = insert_implicit_multiplication(tokenize("2pi"))
        assert [token.text for token in tokens] == ["2", "*", "pi"]


class TestMathErrors:
    def test_division_by_zero(self) -> None:
        with pytest.raises(MathError, match="divide by zero"):
            evaluate("1 / 0")

    def test_modulo_by_zero(self) -> None:
        with pytest.raises(MathError, match="divisor of zero"):
            evaluate("7 % 0")

    def test_square_root_of_a_negative(self) -> None:
        with pytest.raises(MathError, match="negative"):
            evaluate("sqrt(-4)")

    def test_logarithm_of_zero(self) -> None:
        with pytest.raises(MathError, match="positive"):
            evaluate("log(0)")

    def test_inverse_sine_out_of_range(self) -> None:
        with pytest.raises(MathError, match="between -1 and 1"):
            evaluate("asin(2)")

    def test_overflow(self) -> None:
        with pytest.raises(MathError, match="too large"):
            evaluate("exp(100000)")

    def test_negative_base_with_fractional_exponent(self) -> None:
        with pytest.raises(MathError, match="whole-number exponent"):
            evaluate("(-8) ^ 0.5")

    def test_math_errors_are_calculator_errors(self) -> None:
        with pytest.raises(CalculatorError):
            evaluate("1 / 0")


class TestStructuralErrors:
    @pytest.mark.parametrize("expression", ["(1 + 2", "sqrt(2", "((3)"])
    def test_missing_closing_parenthesis(self, expression: str) -> None:
        with pytest.raises(ParseError, match="Unbalanced parentheses"):
            evaluate(expression)

    @pytest.mark.parametrize("expression", ["1 + 2)", "3))"])
    def test_unexpected_closing_parenthesis(self, expression: str) -> None:
        with pytest.raises(ParseError, match="unexpected"):
            evaluate(expression)

    @pytest.mark.parametrize("expression", ["1 +", "2 *", "4 ^"])
    def test_trailing_operator(self, expression: str) -> None:
        with pytest.raises(ParseError, match="missing a value"):
            evaluate(expression)

    @pytest.mark.parametrize("expression", ["", "   ", "\t"])
    def test_empty_expression(self, expression: str) -> None:
        with pytest.raises(ParseError, match="empty"):
            evaluate(expression)


class TestFormatting:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (4.0, "4"),
            (0.0, "0"),
            (-2.5, "-2.5"),
            (0.1 + 0.2, "0.3"),
            (1e15, "1e+15"),
            (1.0 / 3.0, "0.333333333333"),
        ],
    )
    def test_format_result(self, value: float, expected: str) -> None:
        assert format_result(value) == expected

    def test_round_trip_through_the_parser(self) -> None:
        value = evaluate("22 / 7")
        assert evaluate(format_result(value)) == pytest.approx(value, rel=1e-9)
