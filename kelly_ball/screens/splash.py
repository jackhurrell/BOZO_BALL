"""Animated BOZO BALL splash screen."""
import math
import tkinter as tk

from ..display import _interp_color
from ..drawing import draw_ball_on_canvas
from ..theme import BG, FG, MUTED, SPLASH_AUDIO_FILENAMES


class SplashMixin:
    def show_splash(self):
        self.clear()
        self.fg_audio.play(SPLASH_AUDIO_FILENAMES)
        self._splash_phase = "init"
        self._splash_glyphs = []
        self._splash_subtitle = None
        self._splash_tick_count = 0
        self._splash_active_idx = 0

        frame = tk.Frame(self.container, bg=BG)
        frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(frame, bg=BG, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        self._splash_canvas = canvas

        canvas.bind("<Button-1>", self._on_splash_click)
        if self._splash_skip_binding is None:
            self._splash_skip_binding = self.bind_all(
                "<Key>", self._on_splash_click
            )

        self.after(50, self._init_splash_layout)

    def _init_splash_layout(self):
        canvas = self._splash_canvas
        if canvas is None or self._splash_phase == "done":
            return
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 50 or h < 50:
            # Fall back to the window's configured geometry. The canvas only
            # reports real dimensions once Tk has laid the window out, which
            # doesn't happen while the window is withdrawn (e.g. in tests).
            try:
                wh = self.geometry().split("+")[0]
                ww, hh = wh.split("x")
                w = max(w, int(ww))
                h = max(h, int(hh))
            except (ValueError, tk.TclError):
                pass
        if w < 50 or h < 50:
            self.after(50, self._init_splash_layout)
            return

        letter_size = min(w // 10, 92)
        ball_size = int(letter_size * 1.05)
        slot_w = int(letter_size * 0.72)
        space_w = slot_w // 2

        # "BOZO BALL" — the two Os are pool balls (1-ball, 8-ball)
        glyphs_spec = [
            ("text", "B"),
            ("ball", 1),
            ("text", "Z"),
            ("ball", 8),
            ("space", None),
            ("text", "B"),
            ("text", "A"),
            ("text", "L"),
            ("text", "L"),
        ]

        total_w = sum(space_w if k == "space" else slot_w for k, _ in glyphs_spec)
        cx = w / 2
        cy = h / 2 - h * 0.04
        start_x = cx - total_w / 2 + slot_w / 2

        x = start_x
        for i, (kind, val) in enumerate(glyphs_spec):
            if kind == "space":
                x += space_w
                continue
            tag = f"splash_glyph_{i}"
            start_y = -ball_size  # off-screen above
            if kind == "text":
                canvas.create_text(
                    x, start_y, text=val, fill=FG,
                    font=("Helvetica", letter_size, "bold"),
                    tags=(tag,),
                )
            else:
                draw_ball_on_canvas(canvas, x, start_y, ball_size, val, tag)
            self._splash_glyphs.append({
                "tag": tag,
                "y": float(start_y),
                "target_y": float(cy),
                "vy": 0.0,
                "active": False,
                "settled": False,
                "bounces": 0,
            })
            x += slot_w

        self._splash_subtitle = canvas.create_text(
            cx, cy + letter_size,
            text="click anywhere to start",
            fill=BG,  # invisible against background — fades in later
            font=("Helvetica", 16, "italic"),
        )

        self._splash_phase = "drop"
        self.after(40, self._splash_tick)

    def _splash_tick(self):
        if self._splash_phase == "done" or self._splash_canvas is None:
            return
        canvas = self._splash_canvas
        self._splash_tick_count += 1

        if self._splash_phase == "drop":
            if (self._splash_tick_count % 3 == 0
                    and self._splash_active_idx < len(self._splash_glyphs)):
                self._splash_glyphs[self._splash_active_idx]["active"] = True
                self._splash_active_idx += 1

            all_done = self._splash_active_idx >= len(self._splash_glyphs)
            for g in self._splash_glyphs:
                if not g["active"] or g["settled"]:
                    if not g["settled"]:
                        all_done = False
                    continue
            for g in self._splash_glyphs:
                if not g["active"] or g["settled"]:
                    continue
                g["vy"] += 1.6  # gravity per frame
                new_y = g["y"] + g["vy"]
                if new_y >= g["target_y"]:
                    if g["vy"] > 6 and g["bounces"] < 1:
                        g["bounces"] += 1
                        g["vy"] = -g["vy"] * 0.42
                        new_y = g["target_y"]
                    else:
                        new_y = g["target_y"]
                        g["vy"] = 0
                        g["settled"] = True
                dy = new_y - g["y"]
                canvas.move(g["tag"], 0, dy)
                g["y"] = new_y
                all_done = False

            settled_count = sum(1 for g in self._splash_glyphs if g["settled"])
            if (settled_count == len(self._splash_glyphs)
                    and self._splash_active_idx >= len(self._splash_glyphs)):
                self._splash_phase = "subtitle"
                self._splash_tick_count = 0

        elif self._splash_phase == "subtitle":
            step = self._splash_tick_count
            t = min(1.0, step / 18)
            canvas.itemconfig(
                self._splash_subtitle,
                fill=_interp_color(BG, MUTED, t),
            )
            if t >= 1.0:
                self._splash_phase = "pulse"
                self._splash_tick_count = 0

        elif self._splash_phase == "pulse":
            t = (math.sin(self._splash_tick_count * 0.12) + 1) / 2
            canvas.itemconfig(
                self._splash_subtitle,
                fill=_interp_color("#5a6370", FG, t),
            )

        if self._splash_phase != "done":
            self.after(30, self._splash_tick)

    def _on_splash_click(self, _event=None):
        if self._splash_phase == "done":
            return
        self._splash_phase = "done"
        self.fg_audio.stop()
        if self._splash_skip_binding is not None:
            try:
                self.unbind_all("<Key>")
            except tk.TclError:
                pass
            self._splash_skip_binding = None
        self._splash_canvas = None
        self.show_setup()
        # The splash is the "intro"; start looping background music with a
        # fade-in now that the user has dismissed it.
        if self.settings.get("background_music_enabled", True):
            self.bg_music.start(with_fade_in=True)
