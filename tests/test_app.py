"""Smoke tests for the Tkinter window.

They need Tkinter and a display. On a headless Linux machine run them under a
virtual display, for example ``xvfb-run -a pytest``; without one they are skipped.
"""

import pytest

tk = pytest.importorskip("tkinter")

from calculator.engine import AngleMode  # noqa: E402
from calculator.history import HistoryStore  # noqa: E402
from calculator.keypad import MEMORY_ROW, KeyAction  # noqa: E402


@pytest.fixture
def app(tmp_path):
    from calculator.app import CalculatorApp

    try:
        window = CalculatorApp(
            history=HistoryStore(path=tmp_path / "history.json"),
            theme_name="light",
            angle_mode=AngleMode.DEGREES,
        )
    except tk.TclError as error:
        pytest.skip(f"no display available: {error}")
    window.withdraw()
    yield window
    window.destroy()


def test_calculate_updates_display_history_and_status(app):
    app.set_expression("2 + 3 * 4")
    assert app.calculate() == 14.0
    assert app.expression == "14"
    assert app._history_list.size() == 1
    assert app.history.load()[0].result == "14"


def test_errors_are_shown_in_the_status_bar(app):
    app.set_expression("1 / 0")
    assert app.calculate() is None
    assert app._status_var.get() == "Cannot divide by zero"


def test_degree_mode_is_used_for_trigonometry(app):
    app.set_expression("sin(30)")
    assert app.calculate() == pytest.approx(0.5)
    app.toggle_angle_mode()
    assert app.angle_mode is AngleMode.RADIANS


def test_memory_keys(app):
    keys = {spec.action: spec for spec in MEMORY_ROW if spec is not None}
    app.set_expression("6")
    app._on_key(keys[KeyAction.MEMORY_STORE])
    app._on_key(keys[KeyAction.MEMORY_ADD])
    assert app.memory.value == 12.0
    app._on_key(keys[KeyAction.MEMORY_CLEAR])
    assert app.memory.is_set is False


def test_theme_toggle_and_clear_history(app):
    app.toggle_theme()
    assert app.theme.name == "dark"
    app.set_expression("1+1")
    app.calculate()
    app.clear_history()
    assert app._history_list.size() == 0
    assert app.history.load() == []
