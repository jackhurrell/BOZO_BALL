"""Shared UI helpers used across screens.

These are mixed into `KellyBallApp` so screen methods can call them as
`self._text_button(...)` / `self._dn(...)` — preserving the original
in-class API.
"""
import tkinter as tk

from ..display import display_name
from ..theme import DEFAULT_BOZO_M_WHITELIST, FG, LINE, PANEL


class ScreenHelpersMixin:
    """Tk widget helpers + the BOZO display-name wrapper."""

    def _text_button(self, parent, text, command, *,
                     bg=PANEL, fg=FG, hover_bg=LINE,
                     font=("Helvetica", 11),
                     padx=12, pady=6):
        """Label-based "button" that respects bg color on macOS.

        tk.Button on macOS falls back to the native rounded-pill style for
        any non-vivid bg, ignoring the bg/fg config. tk.Label honors bg
        reliably, so we fake a button with click + hover bindings.
        """
        btn = tk.Label(
            parent, text=text, bg=bg, fg=fg,
            font=font, padx=padx, pady=pady,
            cursor="hand2",
        )

        def on_enter(_e=None):
            try:
                btn.config(bg=hover_bg)
            except tk.TclError:
                pass

        def on_leave(_e=None):
            try:
                btn.config(bg=bg)
            except tk.TclError:
                pass

        def on_click(_e=None):
            if command:
                command()

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        btn.bind("<Button-1>", on_click)
        return btn

    def _dn(self, name: str) -> str:
        """Apply user-configured BOZO settings to display a name."""
        return display_name(
            name,
            enabled=bool(self.settings.get("bozo_enabled", True)),
            whitelist=frozenset(
                s.lower() for s in self.settings.get(
                    "whitelist", DEFAULT_BOZO_M_WHITELIST
                )
            ),
        )
