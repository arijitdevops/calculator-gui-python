"""Declarative keypad layouts and the ttk grid builder that renders them."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from tkinter import ttk
from typing import Callable, List, Sequence

__all__ = [
    "KeyAction",
    "KeySpec",
    "MEMORY_ROW",
    "SCIENTIFIC_LAYOUT",
    "STANDARD_LAYOUT",
    "build_keypad",
]


class KeyAction(Enum):
    """What pressing a key should do."""

    INSERT = auto()
    EQUALS = auto()
    CLEAR_ALL = auto()
    CLEAR_ENTRY = auto()
    BACKSPACE = auto()
    TOGGLE_SIGN = auto()
    MEMORY_CLEAR = auto()
    MEMORY_RECALL = auto()
    MEMORY_STORE = auto()
    MEMORY_ADD = auto()
    MEMORY_SUBTRACT = auto()


@dataclass(frozen=True)
class KeySpec:
    """A single button.

    Attributes:
        label: Text drawn on the button.
        action: The behaviour to run when pressed.
        payload: Text inserted when ``action`` is :attr:`KeyAction.INSERT`.
        style: Name of the ttk style, which controls the colour.
        columnspan: How many grid columns the button occupies.
    """

    label: str
    action: KeyAction
    payload: str = ""
    style: str = "Digit.TButton"
    columnspan: int = 1


def _digit(label: str) -> KeySpec:
    return KeySpec(label, KeyAction.INSERT, label, "Digit.TButton")


def _operator(label: str, payload: str | None = None) -> KeySpec:
    return KeySpec(label, KeyAction.INSERT, payload or label, "Operator.TButton")


def _function(label: str, payload: str) -> KeySpec:
    return KeySpec(label, KeyAction.INSERT, payload, "Function.TButton")


#: Four-column keypad shown in both modes.
STANDARD_LAYOUT: List[List[KeySpec]] = [
    [
        KeySpec("C", KeyAction.CLEAR_ALL, style="Danger.TButton"),
        KeySpec("CE", KeyAction.CLEAR_ENTRY, style="Operator.TButton"),
        KeySpec("⌫", KeyAction.BACKSPACE, style="Operator.TButton"),
        _operator("÷", "/"),
    ],
    [_digit("7"), _digit("8"), _digit("9"), _operator("×", "*")],
    [_digit("4"), _digit("5"), _digit("6"), _operator("-")],
    [_digit("1"), _digit("2"), _digit("3"), _operator("+")],
    [
        KeySpec("+/-", KeyAction.TOGGLE_SIGN, style="Operator.TButton"),
        _digit("0"),
        _digit("."),
        KeySpec("=", KeyAction.EQUALS, style="Accent.TButton"),
    ],
]

#: Five-column panel of scientific keys, shown only in scientific mode.
SCIENTIFIC_LAYOUT: List[List[KeySpec]] = [
    [
        _function("sin", "sin("),
        _function("cos", "cos("),
        _function("tan", "tan("),
        _operator("(", "("),
        _operator(")", ")"),
    ],
    [
        _function("asin", "asin("),
        _function("acos", "acos("),
        _function("atan", "atan("),
        _operator("^"),
        _operator("%"),
    ],
    [
        _function("ln", "ln("),
        _function("log", "log("),
        _function("√", "sqrt("),
        _function("exp", "exp("),
        _function("|x|", "abs("),
    ],
    [
        _function("floor", "floor("),
        _function("ceil", "ceil("),
        _function("n!", "!"),
        _function("π", "pi"),
        _function("e", "e"),
    ],
]

#: Memory keys, rendered as a single row above the keypad.
MEMORY_ROW: List[KeySpec] = [
    KeySpec("MC", KeyAction.MEMORY_CLEAR, style="Memory.TButton"),
    KeySpec("MR", KeyAction.MEMORY_RECALL, style="Memory.TButton"),
    KeySpec("M+", KeyAction.MEMORY_ADD, style="Memory.TButton"),
    KeySpec("M-", KeyAction.MEMORY_SUBTRACT, style="Memory.TButton"),
    KeySpec("MS", KeyAction.MEMORY_STORE, style="Memory.TButton"),
]


def build_keypad(
    parent: ttk.Frame,
    layout: Sequence[Sequence[KeySpec]],
    on_key: Callable[[KeySpec], None],
    *,
    padding: int = 3,
) -> ttk.Frame:
    """Render ``layout`` as a grid of buttons inside a new frame.

    Args:
        parent: Container the frame is placed in (the caller still grids it).
        layout: Rows of key specifications.
        on_key: Called with the :class:`KeySpec` of whichever button is pressed.
        padding: Pixels of padding around each button.

    Returns:
        The frame holding the buttons, with all rows and columns weighted so the
        keypad grows with the window.
    """
    frame = ttk.Frame(parent)
    columns = max((len(row) for row in layout), default=0)
    for column in range(columns):
        frame.columnconfigure(column, weight=1, uniform="keys")

    for row_index, row in enumerate(layout):
        frame.rowconfigure(row_index, weight=1)
        column_index = 0
        for spec in row:
            button = ttk.Button(
                frame,
                text=spec.label,
                style=spec.style,
                takefocus=False,
                command=lambda bound=spec: on_key(bound),
            )
            button.grid(
                row=row_index,
                column=column_index,
                columnspan=spec.columnspan,
                sticky="nsew",
                padx=padding,
                pady=padding,
            )
            column_index += spec.columnspan
    return frame
