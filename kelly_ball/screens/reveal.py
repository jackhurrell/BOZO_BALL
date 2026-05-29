"""Reveal screen: per-player name → ball stages, BOZO flash, ball draw."""
import random
import tkinter as tk
from datetime import date
from tkinter import messagebox

from ..drawing import animate_ball_reveal, draw_ball
from ..persistence import save_roster
from ..theme import (
    ACCENT,
    BG,
    BOZO_FLASH_VISUAL_MS,
    BOZO_SURPRISE_IMAGE_MS,
    BOZO_SURPRISE_TEXT_MS,
    BOZO_YELLOW,
    FG,
    MAX_PLAYERS,
    MUTED,
)


class RevealMixin:
    # ---------- Tournament state machine helpers ----------
    def _next_tournament_round(self, advancing: list[str]):
        """Start the next tournament round with the given subset of players."""
        if len(advancing) < 2:
            # 0 or 1 left → crown the champion
            self.show_champion(advancing[0] if advancing else None)
            return
        self.tournament_round += 1
        save_roster(self.roster_path, self.roster)
        balls = random.sample(range(1, MAX_PLAYERS + 1), len(advancing))
        self.assignments = list(zip(advancing, balls))
        self.last_names = list(advancing)
        self.current_winners = set()
        self.reveal_index = 0
        self.reveal_stage = "name"
        self.show_reveal()

    def _record_winner(self, name: str):
        """Increment win count for `name` in the roster, persist."""
        key = name.lower()
        for entry in self.roster:
            if entry["name"].lower() == key:
                entry["wins"] = int(entry.get("wins", 0)) + 1
                break
        else:
            self.roster.append({
                "name": name, "last_played": date.today().isoformat(),
                "games": 1, "wins": 1, "enabled": True,
            })
        self.current_winners.add(name)
        save_roster(self.roster_path, self.roster)

    # ---------- BOZO flash (one-time per bozoified player) ----------
    def _is_surprise_mode(self) -> bool:
        return bool(self.settings.get("bozo_surprise_mode", False))

    def _bozo_flash_total_ms(self) -> int:
        """How long the whole BOZO flash sequence holds the screen."""
        if self._is_surprise_mode():
            return BOZO_SURPRISE_TEXT_MS + BOZO_SURPRISE_IMAGE_MS
        return BOZO_FLASH_VISUAL_MS

    def _render_bozo_flash(self):
        """Dispatcher — mode 1 shows the image directly; mode 2 plays the
        text pop-in first then swaps to the image."""
        if self._is_surprise_mode():
            self._render_bozo_surprise()
        else:
            self._render_bozo_image()

    def _render_bozo_image(self):
        """Render the BOZO image full-screen as the only thing on the page."""
        self.clear()
        frame = tk.Frame(self.container, bg=BG)
        frame.pack(fill="both", expand=True)
        self._fill_bozo_image(frame)

    def _render_bozo_surprise(self):
        """Mode 2: animated 'BOZO' + 🤡 text pop-in, then the clown image."""
        self.clear()
        frame = tk.Frame(self.container, bg=BG)
        frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(frame, bg=BG, highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        # Pop-in animation: scale text + emoji from small to large over the
        # text-phase duration. Frame interval driven by self.after.
        steps = 8
        interval_ms = max(1, BOZO_SURPRISE_TEXT_MS // steps)

        def draw(step: int):
            if not canvas.winfo_exists():
                return
            canvas.delete("all")
            w = canvas.winfo_width() or 760
            h = canvas.winfo_height() or 560
            scale = min(1.0, step / steps)
            text_size = int(28 + (110 - 28) * scale)
            emoji_size = int(40 + (160 - 40) * scale)
            canvas.create_text(
                w / 2, h / 2 - 40,
                text="🤡", font=("Helvetica", emoji_size),
            )
            canvas.create_text(
                w / 2, h / 2 + 80,
                text="BOZO", font=("Helvetica", text_size, "bold"),
                fill=BOZO_YELLOW,
            )

        def tick(step: int):
            draw(step)
            if step < steps:
                self.after(interval_ms, lambda: tick(step + 1))

        tick(1)

        # After the text phase, swap to the image overlay.
        def show_image():
            if not frame.winfo_exists():
                return
            for w in frame.winfo_children():
                w.destroy()
            self._fill_bozo_image(frame)

        self.after(BOZO_SURPRISE_TEXT_MS, show_image)

    def _fill_bozo_image(self, frame):
        """Place the clown image (or text fallback) into ``frame``."""
        # Late import: resolves to the package-level function so test
        # monkeypatches on ``kelly_ball._resource_dir`` take effect.
        from kelly_ball import find_intro_image
        path = find_intro_image()
        rendered = False
        if path is not None:
            try:
                self._intro_image = tk.PhotoImage(file=str(path))
                tk.Label(
                    frame, image=self._intro_image, bg=BG, borderwidth=0,
                ).place(relx=0.5, rely=0.5, anchor="center")
                rendered = True
            except tk.TclError:
                self._intro_image = None
                rendered = False

        if not rendered:
            tk.Label(
                frame, text="🤡",
                font=("Helvetica", 120), fg=BOZO_YELLOW, bg=BG,
            ).place(relx=0.5, rely=0.45, anchor="center")
            tk.Label(
                frame, text="BOZO",
                font=("Helvetica", 48, "bold"), fg=BOZO_YELLOW, bg=BG,
            ).place(relx=0.5, rely=0.65, anchor="center")

    # ---------- Reveal screen ----------
    def show_reveal(self):
        # BOZO flash: if the upcoming "ball" view belongs to a player whose
        # name gets bozoified, slap the BOZO image on the screen for a
        # half-second first, then re-enter this method (with the flag set)
        # to draw the real ball reveal.
        if self.reveal_stage == "ball" and not self._bozo_flash_done:
            name, _ = self.assignments[self.reveal_index]
            if self._dn(name) != name:
                self._render_bozo_flash()
                self._bozo_flash_done = True
                self.after(self._bozo_flash_total_ms(), self.show_reveal)
                return

        self.clear()
        frame = tk.Frame(self.container, bg=BG)
        frame.pack(fill="both", expand=True, padx=32, pady=24)

        # Top bar: cancel-to-main on the left, progress in the centre.
        top_row = tk.Frame(frame, bg=BG)
        top_row.pack(fill="x")
        self._text_button(
            top_row, "✕ Cancel", self._cancel_reveal,
            font=("Helvetica", 11), padx=10, pady=6,
        ).pack(side="left")
        progress = f"Player {self.reveal_index + 1} of {len(self.assignments)}"
        if self.tournament_mode:
            progress = f"Round {self.tournament_round} • " + progress
        tk.Label(
            top_row, text=progress,
            font=("Helvetica", 12), fg=MUTED, bg=BG,
        ).pack(side="right", pady=6)

        body = tk.Frame(frame, bg=BG)
        body.pack(fill="both", expand=True)

        name, ball = self.assignments[self.reveal_index]

        if self.reveal_stage == "name":
            # Surprise mode keeps the BOZO swap hidden until the ball reveal,
            # so the player sees only their real name here.
            shown_name = name if self._is_surprise_mode() else self._dn(name)
            tk.Label(
                body, text="NEXT PLAYER COMING UP",
                font=("Helvetica", 18, "bold"), fg=MUTED, bg=BG,
            ).pack(pady=(60, 12))
            tk.Label(
                body, text=shown_name,
                font=("Helvetica", 48, "bold"), fg=FG, bg=BG,
                wraplength=680, justify="center",
            ).pack()
            hint = "Pass the screen to this player, then click Next"
        else:
            tk.Label(
                body, text="YOUR BALL",
                font=("Helvetica", 18, "bold"), fg=MUTED, bg=BG,
            ).pack(pady=(40, 16))
            self._animate_ball_reveal(body, ball)
            tk.Label(
                body, text="Remember it! Then click Next.",
                font=("Helvetica", 12), fg=MUTED, bg=BG,
            ).pack(pady=(16, 0))
            hint = ""

        btn_row = tk.Frame(frame, bg=BG)
        btn_row.pack(fill="x", pady=(12, 0))
        if hint:
            tk.Label(
                btn_row, text=hint,
                font=("Helvetica", 11, "italic"), fg=MUTED, bg=BG,
            ).pack(side="left")

        self._next_btn = tk.Button(
            btn_row, text="Next  →",
            font=("Helvetica", 14, "bold"),
            bg=ACCENT, fg="#0a0a0a", activebackground="#16a34a",
            disabledforeground="#0a0a0a",
            relief="flat", padx=18, pady=10, cursor="hand2",
            command=self.advance_reveal,
        )
        self._next_btn.pack(side="right")

    def _cancel_reveal(self):
        """Confirm and bail out of the in-progress reveal back to setup."""
        try:
            ok = messagebox.askyesno(
                "BOZO Ball",
                "Cancel this draw and return to the main screen? "
                "The current assignments will be lost.",
            )
        except tk.TclError:
            ok = True
        if not ok:
            return
        self.assignments = []
        self.reveal_index = 0
        self.reveal_stage = "name"
        self._bozo_flash_done = False
        self.current_winners = set()
        self.tournament_round = 0
        self.show_setup()

    def advance_reveal(self):
        if self.reveal_stage == "name":
            self.reveal_stage = "ball"
            self._bozo_flash_done = False  # arm the flash for this player
            self.show_reveal()
            return
        # stage was "ball" — move to next player
        self.reveal_index += 1
        if self.reveal_index >= len(self.assignments):
            self.show_summary()
        else:
            self.reveal_stage = "name"
            self._bozo_flash_done = False
            self.show_reveal()

    # ---------- Ball drawing (delegated to drawing.py) ----------
    def _draw_ball(self, parent, ball: int, size: int = 180):
        draw_ball(parent, ball, size)

    def _animate_ball_reveal(self, parent, ball: int, final_size: int = 180):
        # Lock the Next button until the animation completes so nobody can
        # advance during the reel and miss their ball.
        if self._next_btn is not None:
            try:
                self._next_btn.config(state="disabled")
            except tk.TclError:
                pass

        def _on_settle():
            if self._next_btn is not None:
                try:
                    self._next_btn.config(state="normal")
                except tk.TclError:
                    pass

        animate_ball_reveal(parent, ball, final_size, on_settle=_on_settle)
