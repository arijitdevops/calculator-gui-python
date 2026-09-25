"""Tkinter front end: window layout, event wiring and application state.

The GUI owns no arithmetic.  It collects text, hands it to
:func:`calculator.engine.evaluate`, and turns
:class:`~calculator.tokens.CalculatorError` into a message in the status bar.
"""

from __future__ import annotations

import logging
import os
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

from .engine import AngleMode, CalculatorError, evaluate, format_result
from .history import HistoryEntry, HistoryStore
from .keypad import MEMORY_ROW, SCIENTIFIC_LAYOUT, STANDARD_LAYOUT, KeyAction, KeySpec, build_keypad
from .memory import MemoryRegister
from .themes import THEMES, Theme, apply_theme, default_theme_name

LOGGER = logging.getLogger(__name__)

__all__ = ["CalculatorApp", "run"]

#: Characters the display accepts.  Everything else is rejected on keystroke.
_ALLOWED_CHARACTERS = frozenset("0123456789.+-*/%^()!abcdefghijklmnopqrstuvwxyz ×÷π√")

_APP_TITLE = "PyCalculator"


class CalculatorApp(tk.Tk):
    """The calculator window.

    Args:
        history: Store used for persisted history.  A default store is created
            when omitted.
        theme_name: Initial theme name; falls back to ``CALCULATOR_THEME``.
        angle_mode: Initial angle mode; falls back to ``CALCULATOR_ANGLE_MODE``.
    """

    def __init__(
        self,
        history: Optional[HistoryStore] = None,
        theme_name: Optional[str] = None,
        angle_mode: Optional[AngleMode] = None,
    ) -> None:
        super().__init__()

        self.history = history if history is not None else HistoryStore()
        self.memory = MemoryRegister()
        self.angle_mode: AngleMode = angle_mode or AngleMode.parse(
            os.environ.get("CALCULATOR_ANGLE_MODE", "")
        )
        self.theme: Theme = THEMES[theme_name if theme_name in THEMES else default_theme_name()]
        self._scientific = tk.BooleanVar(value=True)
        self._expression_var = tk.StringVar()
        self._preview_var = tk.StringVar(value="")
        self._status_var = tk.StringVar(value="Ready")
        self._memory_var = tk.StringVar(value="M off")
        self._angle_var = tk.StringVar(value=self.angle_mode.label)
        self._entries: list[HistoryEntry] = []
        self._last_result: Optional[float] = None
        self._style = ttk.Style(self)

        self.title(_APP_TITLE)
        self.minsize(720, 520)

        self._build_widgets()
        self._bind_keys()
        self._load_history()
        self._apply_theme(self.theme)
        self._display.focus_set()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _build_widgets(self) -> None:
        """Create and grid every widget in the window."""
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(1, weight=1)

        self._build_menu()

        header = ttk.Frame(self, padding=(12, 12, 12, 6))
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, textvariable=self._preview_var, style="Muted.TLabel", anchor="e").grid(
            row=0, column=0, sticky="ew"
        )

        validate = (self.register(self._validate_keystroke), "%S")
        self._display = ttk.Entry(
            header,
            textvariable=self._expression_var,
            style="Display.TEntry",
            font=("Consolas", 20),
            justify="right",
            validate="key",
            validatecommand=validate,
        )
        self._display.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        left = ttk.Frame(self, padding=(12, 6, 6, 6))
        left.grid(row=1, column=0, sticky="nsew")
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=2)
        left.rowconfigure(3, weight=3)

        controls = ttk.Frame(left)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(0, weight=1)
        ttk.Checkbutton(
            controls,
            text="Scientific keys",
            variable=self._scientific,
            command=self._refresh_keypad_mode,
            takefocus=False,
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(
            controls,
            text="Angle mode",
            style="Operator.TButton",
            takefocus=False,
            command=self.toggle_angle_mode,
        ).grid(row=0, column=1, sticky="e", padx=(6, 0))

        memory_frame = build_keypad(left, [MEMORY_ROW], self._on_key)
        memory_frame.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        self._scientific_frame = build_keypad(left, SCIENTIFIC_LAYOUT, self._on_key)
        self._scientific_frame.grid(row=2, column=0, sticky="nsew", pady=(6, 0))

        standard_frame = build_keypad(left, STANDARD_LAYOUT, self._on_key)
        standard_frame.grid(row=3, column=0, sticky="nsew", pady=(6, 0))

        right = ttk.Frame(self, padding=(6, 6, 12, 6))
        right.grid(row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        ttk.Label(right, text="History", style="Heading.TLabel").grid(row=0, column=0, sticky="w")

        list_frame = ttk.Frame(right)
        list_frame.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self._history_list = tk.Listbox(
            list_frame,
            activestyle="none",
            borderwidth=1,
            relief="flat",
            highlightthickness=1,
            font=("Consolas", 10),
            exportselection=False,
        )
        self._history_list.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self._history_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._history_list.configure(yscrollcommand=scrollbar.set)
        self._history_list.bind("<<ListboxSelect>>", self._on_history_click)
        self._history_list.bind("<Double-Button-1>", self._on_history_double_click)

        ttk.Label(
            right,
            text="Click an entry to reuse the expression, double-click for the result.",
            style="Muted.TLabel",
            wraplength=260,
            justify="left",
        ).grid(row=2, column=0, sticky="ew", pady=(6, 0))

        ttk.Button(
            right,
            text="Clear history",
            style="Operator.TButton",
            takefocus=False,
            command=self.clear_history,
        ).grid(row=3, column=0, sticky="ew", pady=(6, 0))

        status = ttk.Frame(self, style="Surface.TFrame")
        status.grid(row=2, column=0, columnspan=2, sticky="ew")
        status.columnconfigure(0, weight=1)
        ttk.Label(status, textvariable=self._status_var, style="Status.TLabel", anchor="w").grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Label(status, textvariable=self._memory_var, style="Status.TLabel").grid(
            row=0, column=1
        )
        ttk.Label(status, textvariable=self._angle_var, style="Status.TLabel").grid(row=0, column=2)

    def _build_menu(self) -> None:
        """Create the menu bar."""
        menubar = tk.Menu(self)

        edit_menu = tk.Menu(menubar, tearoff=False)
        edit_menu.add_command(label="Copy result\tCtrl+C", command=self.copy_to_clipboard)
        edit_menu.add_command(label="Paste\tCtrl+V", command=self.paste_from_clipboard)
        edit_menu.add_separator()
        edit_menu.add_command(label="Clear\tEsc", command=self.clear_all)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=False)
        self._theme_var = tk.StringVar(value=self.theme.name)
        for name in sorted(THEMES):
            view_menu.add_radiobutton(
                label=f"{name.capitalize()} theme",
                value=name,
                variable=self._theme_var,
                command=lambda chosen=name: self.set_theme(chosen),
            )
        view_menu.add_separator()
        view_menu.add_checkbutton(
            label="Scientific keys",
            variable=self._scientific,
            command=self._refresh_keypad_mode,
        )
        view_menu.add_separator()
        self._angle_menu_var = tk.StringVar(value=self.angle_mode.value)
        for mode in AngleMode:
            view_menu.add_radiobutton(
                label=mode.label,
                value=mode.value,
                variable=self._angle_menu_var,
                command=lambda chosen=mode: self.set_angle_mode(chosen),
            )
        menubar.add_cascade(label="View", menu=view_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.configure(menu=menubar)

    def _bind_keys(self) -> None:
        """Bind the keyboard shortcuts that Tk does not provide for free."""
        self.bind("<Return>", self._on_return)
        self.bind("<KP_Enter>", self._on_return)
        self.bind("<Escape>", lambda _event: self.clear_all())
        self.bind("<Control-c>", lambda _event: self.copy_to_clipboard())
        self.bind("<Control-C>", lambda _event: self.copy_to_clipboard())
        self.bind("<Control-v>", lambda _event: self.paste_from_clipboard())
        self.bind("<Control-V>", lambda _event: self.paste_from_clipboard())
        self.bind("<F2>", lambda _event: self.toggle_angle_mode())
        self.bind("<F3>", lambda _event: self.toggle_theme())

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------
    def _validate_keystroke(self, inserted: str) -> bool:
        """Reject characters the tokenizer could never accept.

        Args:
            inserted: The text Tk is about to insert (``%S``).

        Returns:
            ``True`` to allow the edit.
        """
        if not inserted:
            return True
        if all(character.lower() in _ALLOWED_CHARACTERS for character in inserted):
            return True
        self.bell()
        self._set_status(f"'{inserted}' is not valid in an expression", error=True)
        return False

    @property
    def expression(self) -> str:
        """The text currently in the display."""
        return self._expression_var.get()

    def set_expression(self, text: str) -> None:
        """Replace the display contents and park the caret at the end."""
        self._expression_var.set(text)
        self._display.icursor(tk.END)

    def insert_text(self, text: str) -> None:
        """Insert ``text`` at the caret."""
        self._display.insert(tk.INSERT, text)
        self._display.focus_set()

    def _set_status(self, message: str, *, error: bool = False) -> None:
        """Show ``message`` in the status bar."""
        self._status_var.set(message)
        if error:
            LOGGER.debug("User-facing error: %s", message)

    def _set_memory_status(self) -> None:
        """Refresh the memory indicator in the status bar."""
        if self.memory.is_set:
            self._memory_var.set(f"M = {format_result(self.memory.value)}")
        else:
            self._memory_var.set("M off")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _on_key(self, spec: KeySpec) -> None:
        """Dispatch a keypad press."""
        action = spec.action
        if action is KeyAction.INSERT:
            self.insert_text(spec.payload)
        elif action is KeyAction.EQUALS:
            self.calculate()
        elif action is KeyAction.CLEAR_ALL:
            self.clear_all()
        elif action is KeyAction.CLEAR_ENTRY:
            self.clear_entry()
        elif action is KeyAction.BACKSPACE:
            self.backspace()
        elif action is KeyAction.TOGGLE_SIGN:
            self.toggle_sign()
        elif action is KeyAction.MEMORY_CLEAR:
            self.memory.clear()
            self._set_memory_status()
            self._set_status("Memory cleared")
        elif action is KeyAction.MEMORY_RECALL:
            self.insert_text(format_result(self.memory.recall()))
        elif action is KeyAction.MEMORY_STORE:
            self._with_current_value(self.memory.store, "Stored {} in memory")
        elif action is KeyAction.MEMORY_ADD:
            self._with_current_value(self.memory.add, "Memory is now {}")
        elif action is KeyAction.MEMORY_SUBTRACT:
            self._with_current_value(self.memory.subtract, "Memory is now {}")
        else:  # pragma: no cover - the enum is exhaustive
            LOGGER.warning("Unhandled key action: %s", action)

    def _with_current_value(self, operation: Callable[[float], float], template: str) -> None:
        """Evaluate the display and feed the result to a memory operation."""
        value = self._current_value()
        if value is None:
            return
        result = operation(value)
        self._set_memory_status()
        self._set_status(template.format(format_result(result)))

    def _current_value(self) -> Optional[float]:
        """Return the numeric value of the display, or ``None`` after an error."""
        text = self.expression.strip()
        if not text:
            return self._last_result if self._last_result is not None else 0.0
        try:
            return evaluate(text, self.angle_mode)
        except CalculatorError as error:
            self._set_status(str(error), error=True)
            self.bell()
            return None

    def calculate(self) -> Optional[float]:
        """Evaluate the display, record the result and show it.

        Returns:
            The result, or ``None`` when the expression could not be evaluated.
        """
        text = self.expression.strip()
        if not text:
            return None
        try:
            value = evaluate(text, self.angle_mode)
        except CalculatorError as error:
            self._set_status(str(error), error=True)
            self.bell()
            return None

        formatted = format_result(value)
        self._last_result = value
        self._preview_var.set(f"{text} =")
        self.set_expression(formatted)
        self._set_status(f"{text} = {formatted}")
        entry = self.history.add(text, formatted)
        self._entries.insert(0, entry)
        self._history_list.insert(0, entry.as_display_text())
        self._trim_history_view()
        return value

    def _trim_history_view(self) -> None:
        """Keep the listbox in step with the store's cap."""
        limit = self.history.limit
        while self._history_list.size() > limit:
            self._history_list.delete(limit)
        del self._entries[limit:]

    def clear_all(self) -> None:
        """Clear the display, the preview line and the last result."""
        self.set_expression("")
        self._preview_var.set("")
        self._last_result = None
        self._set_status("Cleared")

    def clear_entry(self) -> None:
        """Clear only the display."""
        self.set_expression("")
        self._set_status("Entry cleared")

    def backspace(self) -> None:
        """Delete the character before the caret, or the selection."""
        try:
            if self._display.selection_present():
                self._display.delete("sel.first", "sel.last")
                return
        except tk.TclError:  # pragma: no cover - platform dependent
            pass
        position = self._display.index(tk.INSERT)
        if position > 0:
            self._display.delete(position - 1, position)

    def toggle_sign(self) -> None:
        """Wrap the display in a unary minus, or strip one that is already there."""
        text = self.expression.strip()
        if not text:
            return
        if text.startswith("-(") and text.endswith(")"):
            self.set_expression(text[2:-1])
        elif text.startswith("-") and text[1:].replace(".", "", 1).isdigit():
            self.set_expression(text[1:])
        elif text.replace(".", "", 1).isdigit():
            self.set_expression(f"-{text}")
        else:
            self.set_expression(f"-({text})")

    def copy_to_clipboard(self) -> None:
        """Copy the display (or the selection) to the system clipboard."""
        try:
            if self._display.selection_present():
                text = self._display.selection_get()
            else:
                text = self.expression
        except tk.TclError:  # pragma: no cover - platform dependent
            text = self.expression
        if not text:
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._set_status("Copied to the clipboard")
        except tk.TclError as error:  # pragma: no cover - platform dependent
            LOGGER.warning("Clipboard copy failed: %s", error)
            self._set_status("The clipboard is unavailable", error=True)

    def paste_from_clipboard(self) -> None:
        """Insert clipboard text, skipping characters the engine cannot read."""
        try:
            text = self.clipboard_get()
        except tk.TclError:
            self._set_status("There is nothing to paste", error=True)
            return
        cleaned = "".join(
            character for character in text if character.lower() in _ALLOWED_CHARACTERS
        )
        if not cleaned:
            self._set_status("The clipboard holds no usable characters", error=True)
            return
        self.insert_text(cleaned)
        if len(cleaned) != len(text):
            self._set_status("Pasted, ignoring characters the calculator cannot use")
        else:
            self._set_status("Pasted from the clipboard")

    def set_angle_mode(self, mode: AngleMode) -> None:
        """Switch between degrees and radians."""
        self.angle_mode = mode
        self._angle_var.set(mode.label)
        self._angle_menu_var.set(mode.value)
        self._set_status(f"Angle mode: {mode.label.lower()}")

    def toggle_angle_mode(self) -> None:
        """Flip the angle mode."""
        self.set_angle_mode(
            AngleMode.RADIANS if self.angle_mode is AngleMode.DEGREES else AngleMode.DEGREES
        )

    def set_theme(self, name: str) -> None:
        """Switch to the named theme."""
        theme = THEMES.get(name)
        if theme is None:
            LOGGER.warning("Ignoring unknown theme %r", name)
            return
        self._apply_theme(theme)
        self._set_status(f"{name.capitalize()} theme")

    def toggle_theme(self) -> None:
        """Flip between the light and dark themes."""
        self.set_theme("dark" if self.theme.name == "light" else "light")

    def _apply_theme(self, theme: Theme) -> None:
        """Apply ``theme`` to the ttk styles and the plain Tk widgets."""
        self.theme = theme
        self._theme_var.set(theme.name)
        apply_theme(self, self._style, theme)
        self._history_list.configure(
            background=theme.surface,
            foreground=theme.foreground,
            selectbackground=theme.accent_background,
            selectforeground=theme.accent_foreground,
            highlightbackground=theme.border,
            highlightcolor=theme.border,
        )

    def clear_history(self) -> None:
        """Empty the history panel and the file behind it."""
        self.history.clear()
        self._entries.clear()
        self._history_list.delete(0, tk.END)
        self._set_status("History cleared")

    def _refresh_keypad_mode(self) -> None:
        """Show or hide the scientific panel."""
        if self._scientific.get():
            self._scientific_frame.grid()
            self._set_status("Scientific keys shown")
        else:
            self._scientific_frame.grid_remove()
            self._set_status("Standard keys only")

    # ------------------------------------------------------------------
    # History panel
    # ------------------------------------------------------------------
    def _load_history(self) -> None:
        """Populate the history panel from the store."""
        self._entries = self.history.load()
        self._history_list.delete(0, tk.END)
        for entry in self._entries:
            self._history_list.insert(tk.END, entry.as_display_text())
        if self._entries:
            self._set_status(f"Loaded {len(self._entries)} past calculations")

    def _selected_entry(self) -> Optional[HistoryEntry]:
        """Return the highlighted history entry, if any."""
        selection = self._history_list.curselection()
        if not selection:
            return None
        index = selection[0]
        if 0 <= index < len(self._entries):
            return self._entries[index]
        return None

    def _on_history_click(self, _event: tk.Event) -> None:
        """Load the selected expression back into the display."""
        entry = self._selected_entry()
        if entry is None:
            return
        self.set_expression(entry.expression)
        self._preview_var.set(f"{entry.expression} = {entry.result}")
        self._set_status("Expression reloaded from history")

    def _on_history_double_click(self, _event: tk.Event) -> str:
        """Load the selected result into the display."""
        entry = self._selected_entry()
        if entry is not None:
            self.set_expression(entry.result)
            self._set_status("Result reloaded from history")
        return "break"

    def _on_return(self, _event: tk.Event) -> str:
        """Evaluate on Enter and stop the event from reaching the entry."""
        self.calculate()
        return "break"

    def _show_about(self) -> None:
        """Show the About dialog."""
        messagebox.showinfo(
            title=f"About {_APP_TITLE}",
            message=(
                f"{_APP_TITLE}\n\n"
                "A desktop scientific calculator built on the Python standard "
                "library. Expressions are parsed with a shunting-yard parser, "
                "never with eval().\n\n"
                f"History file: {self.history.path}"
            ),
            parent=self,
        )


def run() -> int:
    """Start the GUI event loop.

    Returns:
        ``0`` on a clean exit, ``1`` when no display is available.
    """
    try:
        app = CalculatorApp()
    except tk.TclError as error:
        LOGGER.error("Could not open a window: %s", error)
        LOGGER.error("Tkinter needs a graphical display; on Linux install python3-tk.")
        return 1
    app.mainloop()
    return 0
