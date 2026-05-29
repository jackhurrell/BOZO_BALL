"""Stateless canvas-drawing helpers: balls, reveal animation, confetti."""
import random
import tkinter as tk

from .theme import BALL_COLORS, BG, CONFETTI_COLORS


def draw_ball_on_canvas(canvas, cx, cy, size, ball, tag):
    color = BALL_COLORS.get(ball, "#666666")
    r = size / 2
    if ball >= 9:
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                           fill="white", outline="", tags=(tag,))
        canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                          start=20, extent=140, fill=color, outline="",
                          tags=(tag,))
        canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                          start=200, extent=140, fill=color, outline="",
                          tags=(tag,))
    else:
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                           fill=color, outline="", tags=(tag,))
    nr = size * 0.26
    canvas.create_oval(cx - nr, cy - nr, cx + nr, cy + nr,
                       fill="white", outline="", tags=(tag,))
    canvas.create_text(cx, cy, text=str(ball),
                       font=("Helvetica", int(size * 0.26), "bold"),
                       fill="#111111", tags=(tag,))


def draw_ball(parent, ball: int, size: int = 180):
    color = BALL_COLORS.get(ball, "#666666")
    canvas = tk.Canvas(
        parent, width=size, height=size,
        bg=BG, highlightthickness=0,
    )
    canvas.pack()

    pad = 8
    if ball >= 9 and ball != 8:
        canvas.create_oval(pad, pad, size - pad, size - pad, fill="white", outline="")
        canvas.create_arc(pad, pad, size - pad, size - pad,
                          start=20, extent=140, fill=color, outline="")
        canvas.create_arc(pad, pad, size - pad, size - pad,
                          start=200, extent=140, fill=color, outline="")
    else:
        canvas.create_oval(pad, pad, size - pad, size - pad, fill=color, outline="")

    center = size / 2
    nr = size * 0.22
    canvas.create_oval(center - nr, center - nr, center + nr, center + nr,
                       fill="white", outline="")
    canvas.create_text(center, center, text=str(ball),
                       font=("Helvetica", int(size * 0.22), "bold"),
                       fill="#111111")
    canvas.create_oval(size * 0.25, size * 0.18, size * 0.45, size * 0.32,
                       fill="", outline="")


def animate_ball_reveal(parent, ball: int, final_size: int = 180,
                        on_settle=None):
    """Slot-reel reveal that cycles through balls then snaps to `ball`.

    `on_settle` is called (no args) once the bounce finishes — used by the
    reveal screen to re-enable the Next button.
    """
    canvas = tk.Canvas(
        parent, width=final_size, height=final_size,
        bg=BG, highlightthickness=0,
    )
    canvas.pack()

    def draw_at_size(s, ball_num):
        canvas.delete("all")
        center = final_size / 2
        r = s / 2
        color = BALL_COLORS.get(ball_num, "#666666")
        if ball_num >= 9 and ball_num != 8:
            canvas.create_oval(center - r, center - r, center + r, center + r,
                               fill="white", outline="")
            canvas.create_arc(center - r, center - r, center + r, center + r,
                              start=20, extent=140, fill=color, outline="")
            canvas.create_arc(center - r, center - r, center + r, center + r,
                              start=200, extent=140, fill=color, outline="")
        else:
            canvas.create_oval(center - r, center - r, center + r, center + r,
                               fill=color, outline="")
        nr = s * 0.22
        canvas.create_oval(center - nr, center - nr, center + nr, center + nr,
                           fill="white", outline="")
        canvas.create_text(center, center, text=str(ball_num),
                           font=("Helvetica", max(8, int(s * 0.22)), "bold"),
                           fill="#111111")

    TICK_TOTAL = 20

    state = {"step": 0}

    def settle():
        draw_at_size(final_size, ball)

        def bounce_down():
            if canvas.winfo_exists():
                draw_at_size(int(final_size * 0.92), ball)
                canvas.after(60, bounce_up)

        def bounce_up():
            if canvas.winfo_exists():
                draw_at_size(final_size, ball)
            if on_settle is not None:
                on_settle()

        canvas.after(70, bounce_down)

    def tick():
        if not canvas.winfo_exists():
            return
        step = state["step"]
        state["step"] += 1
        shown = (step % 15) + 1
        if step < TICK_TOTAL:
            growth = min(1.0, step / 12)
            size = int(20 + (final_size - 20) * growth)
            draw_at_size(size, shown)
            if step < 12:
                delay = 35
            elif step < 17:
                delay = 55
            else:
                delay = 80
            canvas.after(delay, tick)
        else:
            settle()

    tick()


def spawn_confetti(canvas, count: int = 60):
    """Spawn falling confetti particles on an existing Canvas."""
    try:
        w = max(canvas.winfo_width(), 760)
        h = max(canvas.winfo_height(), 560)
    except tk.TclError:
        return
    particles = []
    for _ in range(count):
        x = random.uniform(0, w)
        y = random.uniform(-h, 0)
        size = random.randint(4, 9)
        color = random.choice(CONFETTI_COLORS)
        item = canvas.create_rectangle(
            x, y, x + size, y + size,
            fill=color, outline="",
        )
        particles.append({
            "id": item,
            "x": x, "y": y,
            "vx": random.uniform(-1.2, 1.2),
            "vy": random.uniform(2.0, 4.5),
            "size": size,
        })

    def tick(remaining=180):
        if remaining <= 0 or not canvas.winfo_exists():
            return
        for p in particles:
            p["vy"] += 0.12
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            try:
                canvas.coords(
                    p["id"], p["x"], p["y"],
                    p["x"] + p["size"], p["y"] + p["size"],
                )
            except tk.TclError:
                return
        canvas.after(30, lambda: tick(remaining - 1))

    canvas.after(30, tick)
