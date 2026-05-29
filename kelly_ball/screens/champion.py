"""Tournament champion screen with confetti."""
import tkinter as tk

from ..drawing import spawn_confetti
from ..theme import BG, BOZO_YELLOW, FG, MUTED


class ChampionMixin:
    def show_champion(self, name: str | None):
        self.clear()
        # Bottom layer: a Canvas filling the container for the confetti.
        bg_canvas = tk.Canvas(
            self.container, bg=BG, highlightthickness=0,
        )
        bg_canvas.pack(fill="both", expand=True)

        # Top layer: content placed over the canvas via place().
        frame = tk.Frame(self.container, bg=BG)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            frame, text="🏆", font=("Helvetica", 80),
            fg=BOZO_YELLOW, bg=BG,
        ).pack(pady=(0, 0))
        tk.Label(
            frame, text="CHAMPION",
            font=("Helvetica", 18, "bold"), fg=MUTED, bg=BG,
        ).pack()
        tk.Label(
            frame,
            text=self._dn(name) if name else "(no winner declared)",
            font=("Helvetica", 42, "bold"), fg=FG, bg=BG,
            wraplength=680, justify="center",
        ).pack(pady=(8, 16))

        self._text_button(
            frame, "New Tournament", self.show_setup,
            font=("Helvetica", 13, "bold"), padx=16, pady=8,
        ).pack()

        self.after(80, lambda: spawn_confetti(bg_canvas, count=60))
        self.after(900, lambda: spawn_confetti(bg_canvas, count=40))
