"""Stats / leaderboard screen."""
import tkinter as tk

from ..theme import ACCENT, BG, DIM, FG, MUTED, PANEL


class StatsMixin:
    def show_stats(self):
        self.clear()
        frame = tk.Frame(self.container, bg=BG)
        frame.pack(fill="both", expand=True, padx=32, pady=24)

        top = tk.Frame(frame, bg=BG)
        top.pack(fill="x")
        self._text_button(
            top, "←  Back", self.show_setup,
            font=("Helvetica", 11), padx=10, pady=6,
        ).pack(side="left")
        tk.Label(
            top, text="📊 Stats", font=("Helvetica", 22, "bold"),
            fg=FG, bg=BG,
        ).pack(side="left", padx=(16, 0))

        total_players = len(self.roster)
        total_appearances = sum(int(e.get("games", 0)) for e in self.roster)
        total_wins = sum(int(e.get("wins", 0)) for e in self.roster)
        agg = tk.Frame(frame, bg=BG)
        agg.pack(fill="x", pady=(18, 12))
        for label, value in (
            ("Players known", total_players),
            ("Total player-appearances", total_appearances),
            ("Wins recorded", total_wins),
        ):
            cell = tk.Frame(agg, bg=PANEL)
            cell.pack(side="left", expand=True, fill="x", padx=(0, 8))
            tk.Label(
                cell, text=str(value), font=("Helvetica", 22, "bold"),
                fg=FG, bg=PANEL,
            ).pack(anchor="w", padx=12, pady=(10, 0))
            tk.Label(
                cell, text=label, font=("Helvetica", 10), fg=MUTED, bg=PANEL,
            ).pack(anchor="w", padx=12, pady=(0, 10))

        body = tk.Frame(frame, bg=BG)
        body.pack(fill="both", expand=True)

        def leaderboard(parent, title, key):
            col = tk.Frame(parent, bg=BG)
            col.pack(side="left", fill="both", expand=True, padx=(0, 8))
            tk.Label(
                col, text=title, font=("Helvetica", 11, "bold"),
                fg=MUTED, bg=BG,
            ).pack(anchor="w", pady=(0, 6))
            sorted_list = sorted(
                self.roster, key=lambda e: int(e.get(key, 0)), reverse=True,
            )[:5]
            if not sorted_list or all(int(e.get(key, 0)) == 0 for e in sorted_list):
                tk.Label(
                    col, text="— no data yet —", font=("Helvetica", 12, "italic"),
                    fg=DIM, bg=BG,
                ).pack(anchor="w")
                return
            for entry in sorted_list:
                val = int(entry.get(key, 0))
                if val == 0:
                    continue
                row = tk.Frame(col, bg=PANEL)
                row.pack(fill="x", pady=2)
                tk.Label(
                    row, text=self._dn(entry["name"]),
                    font=("Helvetica", 13), fg=FG, bg=PANEL,
                    anchor="w", padx=12, pady=8,
                ).pack(side="left", fill="x", expand=True)
                tk.Label(
                    row, text=str(val), font=("Helvetica", 13, "bold"),
                    fg=ACCENT, bg=PANEL, padx=12,
                ).pack(side="right")

        leaderboard(body, "🏆  Top winners", "wins")
        leaderboard(body, "🎱  Most games played", "games")
