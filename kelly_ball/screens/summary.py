"""Summary screen: per-player ball reveal, winner toggle, next round / new game."""
import random
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from ..persistence import save_roster
from ..theme import (
    ACCENT,
    BALL_COLORS,
    BG,
    BOZO_TEXT_DARK,
    BOZO_YELLOW,
    DIM,
    FG,
    LINE,
    MAX_PLAYERS,
    MUTED,
    PANEL,
)


class SummaryMixin:
    def show_summary(self):
        self.clear()
        frame = tk.Frame(self.container, bg=BG)
        frame.pack(fill="both", expand=True, padx=32, pady=24)

        header = "Round complete!" if self.tournament_mode else "All balls drawn"
        sub = ("Tap 🏆 next to the winners — they advance to the next round."
               if self.tournament_mode
               else "Tap 🏆 to record a winner. Hold Show to peek at a ball.")

        # Top row: title on the left, settings shortcut on the right so the
        # user can toggle music / BOZO mode mid-game without losing state.
        title_row = tk.Frame(frame, bg=BG)
        title_row.pack(fill="x")
        title_col = tk.Frame(title_row, bg=BG)
        title_col.pack(side="left", fill="x", expand=True)
        tk.Label(
            title_col, text=header,
            font=("Helvetica", 24, "bold"), fg=FG, bg=BG,
        ).pack(anchor="w")
        if self.tournament_mode:
            tk.Label(
                title_col,
                text=f"Round {self.tournament_round} • {len(self.assignments)} players",
                font=("Helvetica", 12), fg=ACCENT, bg=BG,
            ).pack(anchor="w", pady=(2, 0))
        self._text_button(
            title_row, "⚙ Settings",
            lambda: self.show_settings(return_to=self.show_summary),
            font=("Helvetica", 11), padx=10, pady=6,
        ).pack(side="right", anchor="n")

        tk.Label(
            frame, text=sub,
            font=("Helvetica", 12), fg=MUTED, bg=BG,
        ).pack(anchor="w", pady=(8, 16))

        list_wrap = tk.Frame(frame, bg=BG)
        list_wrap.pack(fill="both", expand=True)

        canvas = tk.Canvas(list_wrap, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG)
        self._summary_inner = inner

        inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=inner, anchor="nw", width=680)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        for idx, (name, ball) in enumerate(self.assignments):
            self._summary_row(inner, idx, name, ball)

        # Late-join row — only useful when there's a free ball left.
        used_balls = {b for _, b in self.assignments}
        if len(used_balls) < MAX_PLAYERS:
            self._render_late_join(frame)

        btn_row = tk.Frame(frame, bg=BG)
        btn_row.pack(fill="x", pady=(16, 0))

        if self.tournament_mode and len(self.assignments) > 1:
            self._next_round_btn = tk.Button(
                btn_row, text="Next Round  →",
                font=("Helvetica", 14, "bold"),
                bg=ACCENT, fg="#0a0a0a", activebackground="#16a34a",
                relief="flat", padx=18, pady=10, cursor="hand2",
                command=self._on_next_round_click,
            )
            self._next_round_btn.pack(side="right")
            self._text_button(
                btn_row, "End Tournament", self.show_setup,
                font=("Helvetica", 11), padx=12, pady=6,
            ).pack(side="right", padx=(0, 10))
        else:
            self._text_button(
                btn_row, "New Game", self.show_setup,
                font=("Helvetica", 13, "bold"), padx=16, pady=8,
            ).pack(side="right")

    def _render_late_join(self, parent):
        """Inline input for adding a player who joined after the draw."""
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="x", pady=(12, 0))
        tk.Label(
            wrap, text="Late join?", font=("Helvetica", 11),
            fg=MUTED, bg=BG,
        ).pack(side="left")
        entry = tk.Entry(
            wrap, bg=PANEL, fg=FG, insertbackground=FG,
            relief="flat", font=("Helvetica", 12), width=20,
            highlightthickness=1, highlightbackground=LINE,
            highlightcolor=LINE, borderwidth=0,
        )
        entry.pack(side="left", fill="x", expand=True, padx=8)

        def submit(_e=None):
            name = entry.get().strip()
            entry.delete(0, "end")
            if name:
                self._add_late_player(name)

        entry.bind("<Return>", submit)
        entry.bind("<KP_Enter>", submit)
        tk.Button(
            wrap, text="+ Add",
            font=("Helvetica", 11, "bold"),
            bg=ACCENT, fg="#0a0a0a", activebackground="#16a34a",
            relief="flat", padx=12, pady=6, cursor="hand2",
            command=submit,
        ).pack(side="left")
        tk.Label(
            wrap,
            text="gets a random unused ball",
            font=("Helvetica", 10, "italic"), fg=DIM, bg=BG,
        ).pack(side="left", padx=(8, 0))

    def _add_late_player(self, name: str):
        """Append a new player to the round with a random unused ball."""
        name = name.strip()
        if not name:
            return
        existing = {n.lower() for n, _ in self.assignments}
        if name.lower() in existing:
            self._toast(f"{name} is already in this round")
            return
        used = {b for _, b in self.assignments}
        available = [b for b in range(1, MAX_PLAYERS + 1) if b not in used]
        if not available:
            self._toast(f"All {MAX_PLAYERS} balls are taken")
            return
        ball = random.choice(available)
        self.assignments.append((name, ball))
        self.last_names.append(name)

        # Mirror what start_draw does for roster bookkeeping so the player
        # shows up in recents / stats and survives across sessions.
        today = date.today().isoformat()
        key = name.lower()
        for entry in self.roster:
            if entry["name"].lower() == key:
                entry["last_played"] = today
                entry["games"] = int(entry.get("games", 0)) + 1
                entry["enabled"] = True
                break
        else:
            self.roster.append({
                "name": name, "last_played": today,
                "games": 1, "wins": 0, "enabled": True,
            })
        save_roster(self.roster_path, self.roster)

        self.show_summary()

    def _on_next_round_click(self):
        winners = [n for n, _ in self.assignments if n in self.current_winners]
        if not winners:
            self._toast("Tap 🏆 to mark at least one winner")
            return
        if len(winners) == len(self.assignments):
            self._toast("Need at least one loser to advance")
            return
        self._next_tournament_round(winners)

    def _toast(self, msg: str):
        try:
            messagebox.showinfo("BOZO Ball", msg)
        except tk.TclError:
            pass

    def _summary_row(self, parent, idx, name, ball):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", pady=4, padx=2)

        name_label = tk.Label(
            row, text=self._dn(name),
            font=("Helvetica", 16, "bold"), fg=FG, bg=PANEL,
            anchor="w", padx=16, pady=12,
        )
        name_label.pack(side="left", fill="x", expand=True)

        is_winner = name in self.current_winners
        win_btn = tk.Button(
            row, text="🏆", font=("Helvetica", 14),
            bg=BOZO_YELLOW if is_winner else PANEL,
            fg=BOZO_TEXT_DARK if is_winner else MUTED,
            activebackground=BOZO_YELLOW, activeforeground=BOZO_TEXT_DARK,
            relief="flat", padx=10, pady=6,
            cursor="hand2",
        )
        win_btn.pack(side="right", padx=(0, 6), pady=8)

        ball_label = tk.Label(
            row, text="●●",
            font=("Helvetica", 16, "bold"), fg=MUTED, bg=PANEL,
            width=6, padx=12,
        )
        ball_label.pack(side="right")

        show_btn = tk.Button(
            row, text="Hold to Show",
            font=("Helvetica", 11, "bold"),
            bg=ACCENT, fg="#0a0a0a", activebackground="#16a34a",
            relief="flat", padx=12, pady=8, cursor="hand2",
        )
        show_btn.pack(side="right", padx=12, pady=8)

        def reveal(_e=None):
            ball_label.config(text=str(ball), fg=BALL_COLORS.get(ball, FG))

        def hide(_e=None):
            ball_label.config(text="●●", fg=MUTED)

        def toggle_winner():
            if name in self.current_winners:
                # Un-mark (also decrement the persistent count).
                self.current_winners.discard(name)
                for entry in self.roster:
                    if entry["name"].lower() == name.lower():
                        entry["wins"] = max(0, int(entry.get("wins", 0)) - 1)
                        break
                save_roster(self.roster_path, self.roster)
                win_btn.config(bg=PANEL, fg=MUTED)
                name_label.config(fg=FG)
            else:
                self._record_winner(name)
                win_btn.config(bg=BOZO_YELLOW, fg=BOZO_TEXT_DARK)
                name_label.config(fg=BOZO_YELLOW)

        if is_winner:
            name_label.config(fg=BOZO_YELLOW)

        win_btn.config(command=toggle_winner)

        show_btn.bind("<ButtonPress-1>", reveal)
        show_btn.bind("<ButtonRelease-1>", hide)
        show_btn.bind("<Leave>", hide)
