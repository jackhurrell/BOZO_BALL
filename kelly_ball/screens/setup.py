"""Chip-style player input screen + chip add/remove logic."""
import random
import tkinter as tk
from datetime import date

from ..persistence import save_roster
from ..theme import (
    ACCENT,
    BG,
    DANGER,
    DIM,
    FG,
    LINE,
    MAX_PLAYERS,
    MUTED,
    PANEL,
)


class SetupMixin:
    _PLACEHOLDER_TEXT = "Type a name…"

    def show_setup(self):
        self.clear()
        self._chip_widgets = {}
        self._status_after_id = None

        # Seed the chip tray: prefer last-game roster (rematch), else any
        # player marked enabled in the saved roster.
        if self.last_names:
            self.current_chips = list(self.last_names)
        else:
            self.current_chips = [
                e["name"] for e in self.roster if e.get("enabled")
            ]

        frame = tk.Frame(self.container, bg=BG)
        frame.pack(fill="both", expand=True, padx=32, pady=24)

        top = tk.Frame(frame, bg=BG)
        top.pack(fill="x")
        title_col = tk.Frame(top, bg=BG)
        title_col.pack(side="left", fill="x", expand=True)
        tk.Label(
            title_col, text="Who's playing tonight?",
            font=("Helvetica", 26, "bold"), fg=FG, bg=BG,
        ).pack(anchor="w")
        tk.Label(
            title_col,
            text="Type a name and press Enter. Or tap a recent…",
            font=("Helvetica", 12), fg=MUTED, bg=BG,
        ).pack(anchor="w", pady=(4, 0))

        ctl_col = tk.Frame(top, bg=BG)
        ctl_col.pack(side="right")
        for label, cmd in (
            ("📊 Stats", self.show_stats),
            ("⚙ Settings", self.show_settings),
        ):
            self._text_button(
                ctl_col, label, cmd,
                font=("Helvetica", 11),
            ).pack(side="left", padx=(6, 0))

        self._tournament_var = tk.BooleanVar(value=self.tournament_mode)

        def _toggle_tournament():
            self.tournament_mode = bool(self._tournament_var.get())

        tournament_row = tk.Frame(frame, bg=BG)
        tournament_row.pack(fill="x", pady=(8, 10))
        tk.Checkbutton(
            tournament_row, text="🏆 Tournament mode (last player standing wins)",
            variable=self._tournament_var, command=_toggle_tournament,
            bg=BG, fg=FG, selectcolor=PANEL, activebackground=BG,
            activeforeground=FG, font=("Helvetica", 11),
            borderwidth=0, highlightthickness=0, cursor="hand2",
        ).pack(side="left")

        # Tray (outer holds focus ring, inner holds chips + entry).
        self._tray_outer = tk.Frame(
            frame, bg=LINE, highlightthickness=0,
        )
        self._tray_outer.pack(fill="x")
        tray_inner = tk.Frame(self._tray_outer, bg=PANEL)
        tray_inner.pack(fill="x", padx=1, pady=1)

        self._chips_row = tk.Frame(tray_inner, bg=PANEL)
        self._chips_row.pack(fill="x", padx=10, pady=10)

        self.input_entry = tk.Entry(
            self._chips_row, bg=PANEL, fg=FG, insertbackground=FG,
            relief="flat", font=("Helvetica", 13), width=22,
            highlightthickness=0, borderwidth=0,
        )
        self.input_entry.bind("<Return>", self._on_entry_submit)
        self.input_entry.bind("<KP_Enter>", self._on_entry_submit)
        self.input_entry.bind("<comma>", self._on_entry_submit)
        self.input_entry.bind("<BackSpace>", self._on_entry_backspace)
        self.input_entry.bind("<FocusIn>", self._on_entry_focus_in)
        self.input_entry.bind("<FocusOut>", self._on_entry_focus_out)

        for w in (self._tray_outer, tray_inner, self._chips_row):
            w.bind("<Button-1>", lambda _e: self.input_entry.focus_set())

        hdr_row = tk.Frame(frame, bg=BG)
        hdr_row.pack(fill="x", pady=(18, 8))
        tk.Label(
            hdr_row, text="RECENTLY PLAYED — TAP TO ADD",
            font=("Helvetica", 10, "bold"), fg=MUTED, bg=BG,
        ).pack(side="left")
        tk.Label(
            hdr_row, text="right-click to forget",
            font=("Helvetica", 11, "italic"), fg=DIM, bg=BG,
        ).pack(side="right")

        self._recents_frame = tk.Frame(frame, bg=BG)
        self._recents_frame.pack(fill="x")

        footer = tk.Frame(frame, bg=BG)
        footer.pack(side="bottom", fill="x", pady=(16, 0))

        self._count_label = tk.Label(
            footer, text="", font=("Helvetica", 11), fg=MUTED, bg=BG,
        )
        self._count_label.pack(side="left")

        self._start_btn = tk.Button(
            footer, text="Start Draw  →",
            font=("Helvetica", 14, "bold"),
            bg=ACCENT, fg="#0a0a0a", activebackground="#16a34a",
            relief="flat", padx=18, pady=10, cursor="hand2",
            command=self.start_draw,
        )
        self._start_btn.pack(side="right")

        self._status_label = tk.Label(
            footer, text="", font=("Helvetica", 11), fg=DIM, bg=BG,
        )
        self._status_label.pack(side="right", padx=(0, 12))

        self._render_chips()
        self._render_recents()
        self._update_footer()
        self._show_placeholder()
        self.input_entry.focus_set()

    # ---- Placeholder behavior ----------------------------------------
    def _show_placeholder(self):
        if self.input_entry is None:
            return
        if not self.input_entry.get():
            self.input_entry.config(fg=DIM)
            self.input_entry.insert(0, self._PLACEHOLDER_TEXT)
            self._placeholder_shown = True

    def _hide_placeholder(self):
        if self.input_entry is None:
            return
        if self._placeholder_shown:
            self.input_entry.delete(0, "end")
            self.input_entry.config(fg=FG)
            self._placeholder_shown = False

    def _on_entry_focus_in(self, _e=None):
        self._hide_placeholder()
        self._set_tray_focused(True)

    def _on_entry_focus_out(self, _e=None):
        if not self.input_entry.get():
            self._show_placeholder()
        self._set_tray_focused(False)

    def _set_tray_focused(self, focused: bool):
        if self._tray_outer is None:
            return
        self._tray_outer.configure(bg=ACCENT if focused else LINE)

    # ---- Entry submit handlers ---------------------------------------
    def _on_entry_submit(self, event=None):
        if self._placeholder_shown:
            return "break"
        text = self.input_entry.get().rstrip(",").strip()
        if event is not None and getattr(event, "keysym", "") == "comma":
            self.input_entry.delete(0, "end")
            if text:
                self.add_chip(text)
            return "break"
        self.input_entry.delete(0, "end")
        if text:
            self.add_chip(text)
        return "break"

    def _on_entry_backspace(self, _e=None):
        if self._placeholder_shown:
            return None
        if not self.input_entry.get() and self.current_chips:
            self.remove_chip(self.current_chips[-1])
            return "break"
        return None

    # ---- Chip add / remove / render ----------------------------------
    def add_chip(self, name: str) -> bool:
        name = name.strip()
        if not name:
            return False
        existing = {n.lower() for n in self.current_chips}
        if name.lower() in existing:
            self._status(f"{name} is already in the game")
            return False
        if len(self.current_chips) >= MAX_PLAYERS:
            self._status(
                f"Max {MAX_PLAYERS} players — Kelly pool only has 15 balls"
            )
            return False
        self.current_chips.append(name)
        self._render_chips()
        self._render_recents()
        self._update_footer()
        return True

    def remove_chip(self, name: str) -> bool:
        for i, existing in enumerate(self.current_chips):
            if existing.lower() == name.lower():
                del self.current_chips[i]
                self._render_chips()
                self._render_recents()
                self._update_footer()
                return True
        return False

    def _render_chips(self):
        if self._chips_row is None or self.input_entry is None:
            return
        for w in list(self._chip_widgets.values()):
            try:
                w.destroy()
            except tk.TclError:
                pass
        self._chip_widgets = {}
        self.input_entry.pack_forget()
        for name in self.current_chips:
            chip = self._make_chip(self._chips_row, name)
            chip.pack(side="left", padx=(0, 6), pady=2)
            self._chip_widgets[name] = chip
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(2, 0))

    def _make_chip(self, parent, name: str) -> tk.Widget:
        # Chips render as the plain raw name in green — the BOZO swap (and
        # yellow colouring) is deliberately deferred to the reveal screen so
        # the prank stays a surprise.
        chip = tk.Frame(parent, bg=ACCENT)
        label = tk.Label(
            chip, text=name,
            bg=ACCENT, fg="#0a0a0a",
            font=("Helvetica", 12, "bold"),
            padx=10, pady=4,
        )
        label.pack(side="left")
        x = tk.Label(
            chip, text="✕", bg=ACCENT, fg="#0a0a0a",
            font=("Helvetica", 11, "bold"),
            padx=8, pady=4, cursor="hand2",
        )
        x.pack(side="left")
        x.bind("<Button-1>", lambda _e, n=name: self.remove_chip(n))
        return chip

    def _render_recents(self):
        if self._recents_frame is None:
            return
        for w in self._recents_frame.winfo_children():
            w.destroy()

        sorted_roster = sorted(
            self.roster,
            key=lambda e: (e.get("last_played", ""), e.get("games", 0)),
            reverse=True,
        )
        chip_set = {n.lower() for n in self.current_chips}

        row = tk.Frame(self._recents_frame, bg=BG)
        row.pack(fill="x")
        for entry in sorted_roster:
            name = entry["name"]
            wins = int(entry.get("wins", 0))
            badge = f"🏆{wins} " if wins > 0 else ""
            in_game = name.lower() in chip_set
            if in_game:
                struck = "̶".join(name) + "̶"
                btn_text = f"✗ {badge}{struck}"
                fg = DIM
            else:
                btn_text = f"+ {badge}{name}"
                fg = FG
            btn = tk.Label(
                row, text=btn_text, bg=BG, fg=fg,
                font=("Helvetica", 12),
                padx=12, pady=6,
                cursor="hand2" if not in_game else "arrow",
                highlightbackground=LINE,
                highlightcolor=LINE,
                highlightthickness=1,
            )
            btn.pack(side="left", padx=(0, 6), pady=(0, 6))
            if not in_game:
                btn.bind(
                    "<Button-1>",
                    lambda _e, n=name: self.add_chip(n),
                )
                btn.bind("<Enter>", lambda _e, b=btn: b.config(bg=PANEL))
                btn.bind("<Leave>", lambda _e, b=btn: b.config(bg=BG))
            btn.bind(
                "<Button-3>",
                lambda e, n=name: self._show_forget_menu(e, n),
            )
            btn.bind(
                "<Button-2>",
                lambda e, n=name: self._show_forget_menu(e, n),
            )

    def _update_footer(self):
        if self._count_label is None or self._start_btn is None:
            return
        n = len(self.current_chips)
        if n >= MAX_PLAYERS:
            self._count_label.configure(
                text=f"{n} of {MAX_PLAYERS} playing — table is full",
                fg=DANGER,
            )
        else:
            self._count_label.configure(
                text=f"{n} of {MAX_PLAYERS} playing", fg=MUTED,
            )
        self._start_btn.configure(state=("normal" if n > 0 else "disabled"))

    def _show_forget_menu(self, event, name: str):
        menu = tk.Menu(self, tearoff=0, bg=PANEL, fg=FG,
                       activebackground=DANGER, activeforeground=FG)
        menu.add_command(
            label=f'Forget "{name}"',
            command=lambda: self._forget_roster_entry(name),
        )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _forget_roster_entry(self, name: str):
        before = len(self.roster)
        self.roster = [e for e in self.roster if e["name"].lower() != name.lower()]
        if len(self.roster) != before:
            save_roster(self.roster_path, self.roster)
            self._render_recents()
            self._status(f"Forgot {name}")

    def _status(self, msg: str):
        if self._status_label is None:
            return
        if self._status_after_id is not None:
            try:
                self.after_cancel(self._status_after_id)
            except tk.TclError:
                pass
            self._status_after_id = None
        self._status_label.configure(text=msg)
        self._status_after_id = self.after(
            2200, lambda: self._status_label.configure(text="")
        )

    # ---- Start draw --------------------------------------------------
    def start_draw(self):
        names = list(self.current_chips)
        if not names:
            self._status("Add at least one player to start")
            return
        if len(names) > MAX_PLAYERS:
            self._status(
                f"Max {MAX_PLAYERS} players — Kelly pool only has 15 balls"
            )
            return

        today = date.today().isoformat()
        by_key = {e["name"].lower(): e for e in self.roster}
        chip_keys = {n.lower() for n in names}
        for n in names:
            key = n.lower()
            if key in by_key:
                entry = by_key[key]
                entry["last_played"] = today
                entry["games"] = int(entry.get("games", 0)) + 1
                entry["enabled"] = True
            else:
                entry = {
                    "name": n, "last_played": today,
                    "games": 1, "wins": 0, "enabled": True,
                }
                self.roster.append(entry)
                by_key[key] = entry
        for entry in self.roster:
            if entry["name"].lower() not in chip_keys:
                entry["enabled"] = False
        save_roster(self.roster_path, self.roster)

        balls = random.sample(range(1, MAX_PLAYERS + 1), len(names))
        self.assignments = list(zip(names, balls))
        self.last_names = list(names)
        self.current_winners = set()
        if self.tournament_mode:
            self.tournament_round = 1
        else:
            self.tournament_round = 0
        self.reveal_index = 0
        self.reveal_stage = "name"
        self.show_reveal()
