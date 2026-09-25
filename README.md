# PyCalculator

A standalone desktop scientific calculator built entirely on the Python standard library. Expressions are parsed by a hand-written tokenizer and shunting-yard parser rather than `eval()`, so the calculator never executes the text you type; it converts it to Reverse Polish Notation and walks that with an operand stack. The interface is Tkinter, which ships with CPython, so the application runs from a clean Python install with nothing to download and can be frozen into a single executable with PyInstaller.

![Python](https://img.shields.io/badge/python-3.9%2B-3776AB)
![GUI](https://img.shields.io/badge/GUI-Tkinter-4B8BBE)
![Dependencies](https://img.shields.io/badge/runtime%20dependencies-none-success)
![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- **No `eval()` anywhere.** A tokenizer, a shunting-yard parser and an RPN evaluator, each in its own module and each independently testable.
- **Scientific functions**: `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `log`, `ln`, `sqrt`, `exp`, `abs`, `floor`, `ceil`, plus the constants `pi`, `e` and `tau`.
- **Full operator set**: `+`, `-`, `*`, `/`, `%` (remainder), `^` (power, right associative), prefix `-`, parentheses and postfix `!` (factorial).
- **Implicit multiplication** so `2pi`, `3(4+1)` and `(1+1)(2+2)` all mean what they look like.
- **Degrees / radians toggle** with the active mode always visible in the status bar.
- **Typed errors surfaced as plain English.** `ParseError` and `MathError` both derive from `CalculatorError`; the window turns them into a status-bar message such as "Cannot divide by zero" or "Unbalanced parentheses: a ')' is missing (at character 7)" instead of a traceback.
- **Memory keys** MC, MR, M+, M- and MS, with the stored value shown in the status bar.
- **Persistent history** in a JSON file under your user config directory, capped at 100 entries, reloaded at start-up. Click an entry to reuse the expression, double-click to reuse the result.
- **Light and dark themes**, switchable from the View menu or with `F3`.
- **Standard and scientific keypad modes**, with the scientific panel hidden in standard mode.
- **Keyboard driven**: type straight into the display, `Enter` evaluates, `Esc` clears, `Ctrl+C`/`Ctrl+V` copy and paste, `F2` flips the angle mode.
- **Single-file executable** via the bundled `calculator.spec`.

## Tech stack

| Layer | Choice |
| --- | --- |
| Language | Python 3.9+ |
| GUI toolkit | Tkinter / ttk (standard library) |
| Maths | `math` (standard library) |
| Persistence | JSON file in the per-user config directory |
| Tests | pytest |
| Packaging | setuptools (`pyproject.toml`), PyInstaller for the executable |
| Linting | ruff |

## Project structure

```
calculator-gui-python/
├── src/
│   └── calculator/
│       ├── __init__.py        # public API re-exports and __version__
│       ├── __main__.py        # python -m calculator entry point, logging setup
│       ├── app.py             # Tkinter window, event wiring, application state
│       ├── engine.py          # shunting-yard parser, RPN evaluator, angle modes
│       ├── tokens.py          # token types, operator tables, tokenizer, errors
│       ├── history.py         # JSON-backed persistent history store
│       ├── keypad.py          # declarative keypad layouts and grid builder
│       ├── memory.py          # MC / MR / M+ / M- / MS register
│       └── themes.py          # light and dark palettes, ttk styling
├── tests/
│   ├── test_app.py            # GUI smoke tests (need a display, e.g. xvfb-run)
│   ├── test_engine.py         # parser precedence, unary minus, functions, errors
│   ├── test_history.py        # persistence, limits, corrupt-file handling
│   └── test_memory.py         # MC / MR / M+ / M- / MS register
├── docs/
│   └── images/                # screenshots referenced by this README
├── calculator.spec            # PyInstaller one-file build recipe
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## Prerequisites

- Python 3.9 or newer.
- Tkinter. It is included with the official Windows and macOS installers. On Debian or Ubuntu install it separately with `sudo apt install python3-tk`; on Fedora `sudo dnf install python3-tkinter`.
- A graphical desktop session. The application exits with a clear message if no display is available.

Check your installation before going further:

```bash
python -c "import tkinter; print(tkinter.TkVersion)"
```

## Installation

Clone the repository and create a virtual environment.

Windows (PowerShell or Command Prompt):

```bat
git clone https://github.com/commonlabs/calculator-gui-python.git
cd calculator-gui-python
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Linux and macOS:

```bash
git clone https://github.com/commonlabs/calculator-gui-python.git
cd calculator-gui-python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The runtime requirements file is intentionally empty of packages; run it anyway so the step is the same for everyone and so the environment is ready if you later install the development extras:

```bash
pip install -r requirements-dev.txt
```

To install the package itself (which gives you the `pycalculator` command):

```bash
pip install -e .
```

## Configuration

Every setting is optional and read from the environment at start-up. Copy `.env.example` to `.env` for reference, then export the variables in your shell or set them in Windows under *System Properties → Environment Variables*. The application reads the process environment directly; it does not parse `.env` itself.

| Variable | Description | Default |
| --- | --- | --- |
| `CALCULATOR_HISTORY_FILE` | Full path to the history JSON file. | `%APPDATA%\PyCalculator\history.json` (Windows), `~/.config/pycalculator/history.json` (Linux), `~/Library/Application Support/PyCalculator/history.json` (macOS) |
| `CALCULATOR_HISTORY_LIMIT` | Maximum number of history entries kept. Non-numeric or non-positive values fall back to the default and log a warning. | `100` |
| `CALCULATOR_THEME` | Start-up theme, `light` or `dark`. | `light` |
| `CALCULATOR_ANGLE_MODE` | Start-up angle mode, `deg` or `rad`. | `rad` |
| `CALCULATOR_LOG_LEVEL` | Root logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`. | `WARNING` |

Example, starting in dark mode with degrees:

```bat
set CALCULATOR_THEME=dark
set CALCULATOR_ANGLE_MODE=deg
python -m calculator
```

## Usage

Install the package into your virtual environment once (see [Installation](#installation)), then start it with either command:

```bash
python -m calculator
pycalculator
```

To run straight from a checkout without installing, put `src` on the path first:

```bash
# Linux / macOS
PYTHONPATH=src python -m calculator
```

```bat
:: Windows (Command Prompt)
set PYTHONPATH=src
python -m calculator
```

Type an expression into the display and press `Enter`, or build it with the keypad. The evaluated expression moves to the grey preview line above the display, the result replaces it in the display, and the pair is appended to the history panel on the right.

### Keyboard shortcuts

| Key | Action |
| --- | --- |
| `0`-`9`, `.` | Type digits directly into the display |
| `+` `-` `*` `/` `%` `^` `(` `)` `!` | Type operators directly into the display |
| Letters | Type function names such as `sqrt(` and constants such as `pi` |
| `Enter` / numeric `Enter` | Evaluate |
| `Esc` | Clear the display, the preview line and the last result |
| `Backspace` | Delete the character before the caret, or the selection |
| `Ctrl+C` | Copy the selection, or the whole display if nothing is selected |
| `Ctrl+V` | Paste, silently dropping characters the engine cannot read |
| `F2` | Toggle degrees / radians |
| `F3` | Toggle light / dark theme |

Characters that could never appear in a valid expression are rejected as you type, with a short explanation in the status bar.

## Expression reference and public API

### Operators

| Symbol | Meaning | Precedence | Associativity |
| --- | --- | --- | --- |
| `+` `-` | Addition, subtraction | 1 | Left |
| `*` `/` `%` | Multiplication, division, remainder | 2 | Left |
| `-` `+` (prefix) | Sign | 3 | Right |
| `^` | Exponentiation | 4 | Right |
| `!` (postfix) | Factorial | Highest | Applies to the value on its left |

Because prefix `-` sits between `*` and `^`, `-2^2` evaluates to `-4` and `-2*3` evaluates to `-6`, matching the usual mathematical reading.

### Functions and constants

| Name | Description |
| --- | --- |
| `sin(x)` `cos(x)` `tan(x)` | Trigonometric functions; the argument is read in the active angle mode |
| `asin(x)` `acos(x)` `atan(x)` | Inverse trigonometric functions; the result is returned in the active angle mode |
| `log(x)` | Base-10 logarithm, `x > 0` |
| `ln(x)` | Natural logarithm, `x > 0` |
| `sqrt(x)` | Square root, `x >= 0` |
| `exp(x)` | `e` raised to `x` |
| `abs(x)` `floor(x)` `ceil(x)` | Magnitude, round down, round up |
| `pi` `e` `tau` | Constants |

### Python API

The engine is importable on its own; it does not pull in Tkinter.

| Callable | Signature | Description |
| --- | --- | --- |
| `evaluate` | `evaluate(expression: str, angle_mode: AngleMode = AngleMode.RADIANS) -> float` | Parse and evaluate an infix expression |
| `tokenize` | `tokenize(expression: str) -> list[Token]` | Text to tokens |
| `to_rpn` | `to_rpn(tokens: Sequence[Token]) -> list[Token]` | Infix tokens to Reverse Polish Notation |
| `evaluate_rpn` | `evaluate_rpn(rpn: Sequence[Token], angle_mode: AngleMode = AngleMode.RADIANS) -> float` | Evaluate an RPN token stream |
| `format_result` | `format_result(value: float, precision: int = 12) -> str` | Render a result the way the display shows it |

Example:

```python
>>> from calculator import evaluate, format_result, AngleMode
>>> evaluate("2 + 3 * 4")
14.0
>>> evaluate("sin(30) + sqrt(16)", AngleMode.DEGREES)
4.5
>>> format_result(evaluate("22 / 7"))
'3.14285714286'
```

Errors are typed:

```python
>>> from calculator import evaluate, MathError, ParseError
>>> try:
...     evaluate("1 / 0")
... except MathError as error:
...     print(error)
Cannot divide by zero
>>> try:
...     evaluate("sqrt(2")
... except ParseError as error:
...     print(error)
Unbalanced parentheses: a ')' is missing (at character 5)
```

### History file format

```json
{
  "version": 1,
  "saved_at": "2026-02-11T09:14:03+00:00",
  "entries": [
    { "expression": "2 + 3 * 4", "result": "14", "timestamp": "2026-02-11T09:14:03+00:00" }
  ]
}
```

Entries are newest first. The file is written atomically through a temporary file, and a corrupt or unreadable file is logged and treated as empty history rather than stopping the application.

## Screenshots

Screenshots belong in `docs/images/` and are referenced from this section, for example:

```markdown
![Standard keypad, light theme](docs/images/standard-light.png)
![Scientific keypad, dark theme](docs/images/scientific-dark.png)
```

The directory currently holds only a `.gitkeep` placeholder; capture your own after running the application.

## Testing

Install the development extras, then run pytest from the repository root:

```bash
pip install -r requirements-dev.txt
pytest
```

`pyproject.toml` puts `src` on the path for pytest, so no installation step is required to run the suite. For coverage:

```bash
pytest --cov=calculator --cov-report=term-missing
```

`tests/test_engine.py` covers operator precedence and associativity, prefix minus in every position, nested function calls, implicit multiplication, both angle modes, factorial edge cases and each error path. `tests/test_history.py` covers persistence, the entry cap, corrupt files and the environment overrides. `tests/test_memory.py` covers the memory register.

`tests/test_app.py` builds the real Tkinter window and drives it (evaluation, error messages, angle mode, memory keys, theme switch, clearing history). It needs a display: on Windows and macOS it simply runs, and on a headless Linux machine or CI runner use a virtual X server:

```bash
sudo apt install xvfb
xvfb-run -a pytest
```

Without a display those five tests are skipped rather than failed.

Lint and format checks:

```bash
ruff check .
ruff format --check .
```

## Building a standalone executable

```bash
pip install -r requirements-dev.txt
pyinstaller calculator.spec
```

The build produces `dist/PyCalculator.exe` on Windows and `dist/PyCalculator` elsewhere, with no console window and no external dependencies. To add an icon, drop an `.ico` file into `docs/images/` and set `ICON_FILE` near the top of `calculator.spec`.

Build on the platform you intend to ship to: PyInstaller does not cross-compile. Antivirus software sometimes flags freshly built, unsigned one-file executables; sign the binary before distributing it.

## Roadmap and limitations

Known limitations:

- Functions take exactly one argument. There is no `atan2`, `min`, `max` or `pow`, and the tokenizer treats a comma as a digit separator rather than an argument separator.
- Arithmetic is IEEE 754 double precision, so results carry the usual floating-point rounding. Results below `1e-12` in magnitude are snapped to zero to keep `cos(90)` in degrees from reading `6.1e-17`.
- Factorial is limited to `170!`, the largest value representable as a float.
- Implicit multiplication means `1 2` is read as `1 * 2`. Whitespace never joins digits.
- There is no variable assignment, no `ans` symbol and no unit conversion.
- GUI tests are smoke tests of the window's public actions; they do not simulate mouse clicks on individual buttons.
- The single memory register holds one value, as on a desk calculator, rather than a bank of named slots.

Possible future work:

- Multi-argument functions and a comma argument separator.
- A variables panel and an `ans` reference to the previous result.
- Arbitrary precision mode backed by `decimal.Decimal`.
- Exportable history (CSV) and a search box over the history panel.
- A GitHub Actions workflow running the suite (including the GUI tests under `xvfb-run`) on Windows, macOS and Linux.

## License

Released under the MIT License. See [LICENSE](LICENSE) for the full text.
