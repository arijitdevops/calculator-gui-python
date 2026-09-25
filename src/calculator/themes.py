"""Colour themes and the ttk styling that applies them."""

from __future__ import annotations

import logging
import os
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Dict, List

LOGGER = logging.getLogger(__name__)

__all__ = ["Theme", "THEMES", "default_theme_name", "apply_theme", "theme_names"]


@dataclass(frozen=True)
class Theme:
    """A flat colour palette for the whole window."""

    name: str
    background: str
    surface: str
    display_background: str
    display_foreground: str
    foreground: str
    muted_foreground: str
    digit_background: str
    operator_background: str
    accent_background: str
    accent_foreground: str
    danger_background: str
    active_background: str
    border: str


LIGHT = Theme(
    name="light",
    background="#f2f3f5",
    surface="#ffffff",
    display_background="#ffffff",
    display_foreground="#15181d",
    foreground="#15181d",
    muted_foreground="#5c6570",
    digit_background="#ffffff",
    operator_background="#e4e7ec",
    accent_background="#1f6feb",
    accent_foreground="#ffffff",
    danger_background="#e5534b",
    active_background="#d7dbe0",
    border="#c9ced6",
)

DARK = Theme(
    name="dark",
    background="#15181d",
    surface="#1d2127",
    display_background="#11141a",
    display_foreground="#f0f3f6",
    foreground="#f0f3f6",
    muted_foreground="#9aa4b1",
    digit_background="#272c34",
    operator_background="#333944",
    accent_background="#3b82f6",
    accent_foreground="#0b0e13",
    danger_background="#e5534b",
    active_background="#3f4652",
    border="#39404b",
)

#: Every theme the application can switch to, keyed by name.
THEMES: Dict[str, Theme] = {LIGHT.name: LIGHT, DARK.name: DARK}


def theme_names() -> List[str]:
    """Return the available theme names in a stable order."""
    return sorted(THEMES)


def default_theme_name() -> str:
    """Return the start-up theme, honouring ``CALCULATOR_THEME``."""
    requested = (os.environ.get("CALCULATOR_THEME") or "").strip().lower()
    if requested in THEMES:
        return requested
    if requested:
        LOGGER.warning("Unknown CALCULATOR_THEME=%r; falling back to 'light'", requested)
    return LIGHT.name


def apply_theme(root: tk.Misc, style: ttk.Style, theme: Theme) -> None:
    """Configure every ttk style used by the application for ``theme``.

    Args:
        root: The toplevel window, used to set the window background.
        style: The shared :class:`ttk.Style` instance.
        theme: The palette to apply.
    """
    try:
        style.theme_use("clam")
    except tk.TclError:  # pragma: no cover - only on exotic Tk builds
        LOGGER.debug("The 'clam' ttk theme is unavailable; keeping the default")

    root.configure(background=theme.background)

    style.configure("TFrame", background=theme.background)
    style.configure("Surface.TFrame", background=theme.surface)
    style.configure("TLabel", background=theme.background, foreground=theme.foreground)
    style.configure("Muted.TLabel", background=theme.background, foreground=theme.muted_foreground)
    style.configure(
        "Status.TLabel",
        background=theme.surface,
        foreground=theme.muted_foreground,
        padding=(8, 4),
    )
    style.configure(
        "Heading.TLabel",
        background=theme.background,
        foreground=theme.foreground,
        font=("Segoe UI", 10, "bold"),
    )
    style.configure(
        "Display.TEntry",
        fieldbackground=theme.display_background,
        foreground=theme.display_foreground,
        insertcolor=theme.display_foreground,
        bordercolor=theme.border,
        lightcolor=theme.border,
        darkcolor=theme.border,
        padding=10,
    )
    style.configure("TLabelframe", background=theme.background, bordercolor=theme.border)
    style.configure(
        "TLabelframe.Label", background=theme.background, foreground=theme.muted_foreground
    )
    style.configure("TNotebook", background=theme.background, bordercolor=theme.border)
    style.configure(
        "TNotebook.Tab",
        background=theme.operator_background,
        foreground=theme.foreground,
        padding=(14, 6),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", theme.surface)],
        foreground=[("selected", theme.foreground)],
    )

    button_variants = {
        "Digit.TButton": (theme.digit_background, theme.foreground),
        "Operator.TButton": (theme.operator_background, theme.foreground),
        "Function.TButton": (theme.operator_background, theme.muted_foreground),
        "Memory.TButton": (theme.operator_background, theme.muted_foreground),
        "Accent.TButton": (theme.accent_background, theme.accent_foreground),
        "Danger.TButton": (theme.danger_background, "#ffffff"),
        "TButton": (theme.operator_background, theme.foreground),
    }
    for style_name, (background, foreground) in button_variants.items():
        style.configure(
            style_name,
            background=background,
            foreground=foreground,
            bordercolor=theme.border,
            focuscolor=theme.accent_background,
            padding=(4, 10),
            relief="flat",
        )
        style.map(
            style_name,
            background=[("pressed", theme.active_background), ("active", theme.active_background)],
            foreground=[("disabled", theme.muted_foreground)],
        )

    style.configure(
        "TCheckbutton",
        background=theme.background,
        foreground=theme.foreground,
        focuscolor=theme.accent_background,
    )
    style.map(
        "TCheckbutton",
        background=[("active", theme.background)],
        indicatorcolor=[("selected", theme.accent_background)],
    )

    style.configure(
        "Vertical.TScrollbar",
        background=theme.operator_background,
        troughcolor=theme.background,
        bordercolor=theme.border,
        arrowcolor=theme.foreground,
    )
