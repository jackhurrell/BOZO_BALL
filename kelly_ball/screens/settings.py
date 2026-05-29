"""Settings screen: BOZO mode selector, background music toggle, whitelist."""
import tkinter as tk

from ..persistence import save_settings
from ..theme import ACCENT, BG, DEFAULT_BOZO_M_WHITELIST, FG, MUTED, PANEL


# Mapping between the StringVar choice and the two underlying settings keys.
# Kept as one declarative table so the radio rendering, apply-on-click, and
# Save / Reset all read from the same source of truth.
BOZO_MODES = (
    # (key,        radio label,                                         bozo_enabled, surprise)
    ("off",      "Off — no BOZO swap and no flash animation",            False, False),
    ("classic",  "Classic — show “BOZO <name>” on the name screen",      True,  False),
    ("surprise", "Surprise — hide BOZO until ball reveal (animated)",    True,  True),
)
BOZO_MODE_BY_KEY = {key: (en, surp) for key, _, en, surp in BOZO_MODES}


def _mode_for(settings: dict) -> str:
    if not bool(settings.get("bozo_enabled", True)):
        return "off"
    return "surprise" if bool(settings.get("bozo_surprise_mode", False)) else "classic"


class SettingsMixin:
    def show_settings(self, return_to=None):
        """Render the settings editor.

        `return_to` is the callback used by Back and Save to leave the
        screen. Defaults to `show_setup` so existing callers (and tests)
        keep working; the summary screen passes `show_summary` so settings
        opened mid-game return to the summary instead of resetting state.
        """
        self.clear()
        return_to = return_to or self.show_setup
        frame = tk.Frame(self.container, bg=BG)
        frame.pack(fill="both", expand=True, padx=32, pady=24)

        top = tk.Frame(frame, bg=BG)
        top.pack(fill="x")
        self._text_button(
            top, "←  Back", return_to,
            font=("Helvetica", 11), padx=10, pady=6,
        ).pack(side="left")
        tk.Label(
            top, text="⚙ Settings", font=("Helvetica", 22, "bold"),
            fg=FG, bg=BG,
        ).pack(side="left", padx=(16, 0))

        body = tk.Frame(frame, bg=BG)
        body.pack(fill="both", expand=True, pady=(18, 0))

        # BOZO mode — single 3-way selector covering "off" and the two on
        # modes. Replaces the prior enable-checkbox + reveal-mode radios.
        # Auto-applies on click so the change is live without needing Save.
        tk.Label(
            body, text="BOZO mode",
            font=("Helvetica", 13, "bold"), fg=FG, bg=BG,
        ).pack(anchor="w")
        tk.Label(
            body,
            text="Off disables the name swap and the clown flash entirely. The whitelist below only applies in Classic / Surprise.",
            font=("Helvetica", 11), fg=MUTED, bg=BG, wraplength=680, justify="left",
        ).pack(anchor="w", pady=(2, 6))

        mode_var = tk.StringVar(value=_mode_for(self.settings))

        def apply_mode():
            en, surp = BOZO_MODE_BY_KEY[mode_var.get()]
            self.settings["bozo_enabled"] = en
            self.settings["bozo_surprise_mode"] = surp
            save_settings(self.settings_path, self.settings)

        for key, label, _, _ in BOZO_MODES:
            tk.Radiobutton(
                body, text=label, value=key, variable=mode_var,
                command=apply_mode,
                bg=BG, fg=FG, selectcolor=PANEL, activebackground=BG,
                activeforeground=FG, font=("Helvetica", 12),
                borderwidth=0, highlightthickness=0, cursor="hand2",
            ).pack(anchor="w")
        tk.Label(body, text="", bg=BG).pack(pady=(0, 12))

        bg_music_var = tk.BooleanVar(
            value=bool(self.settings.get("background_music_enabled", True))
        )
        tk.Checkbutton(
            body, text="Play looping background music",
            variable=bg_music_var,
            bg=BG, fg=FG, selectcolor=PANEL, activebackground=BG,
            activeforeground=FG, font=("Helvetica", 13),
            borderwidth=0, highlightthickness=0, cursor="hand2",
        ).pack(anchor="w", pady=(0, 18))

        tk.Label(
            body, text="Whitelist (one name per line — these stay un-bozo'd):",
            font=("Helvetica", 12, "bold"), fg=FG, bg=BG,
        ).pack(anchor="w")

        whitelist_text = tk.Text(
            body, height=8, font=("Helvetica", 13),
            bg=PANEL, fg=FG, insertbackground=FG,
            relief="flat", padx=10, pady=8,
        )
        whitelist_text.pack(fill="x", pady=(6, 0))
        whitelist_text.insert(
            "1.0", "\n".join(self.settings.get("whitelist", DEFAULT_BOZO_M_WHITELIST))
        )

        def save():
            wl_raw = whitelist_text.get("1.0", "end").splitlines()
            wl = [line.strip() for line in wl_raw if line.strip()]
            en, surp = BOZO_MODE_BY_KEY[mode_var.get()]
            self.settings["bozo_enabled"] = en
            self.settings["bozo_surprise_mode"] = surp
            new_bg = bool(bg_music_var.get())
            prev_bg = bool(self.settings.get("background_music_enabled", True))
            self.settings["background_music_enabled"] = new_bg
            self.settings["whitelist"] = wl
            save_settings(self.settings_path, self.settings)
            # React to the bg-music toggle immediately so the user hears
            # the change without restarting.
            if new_bg and not prev_bg:
                self.bg_music.start(with_fade_in=True)
            elif prev_bg and not new_bg:
                self.bg_music.stop()
            return_to()

        def reset():
            mode_var.set("classic")
            apply_mode()
            bg_music_var.set(True)
            whitelist_text.delete("1.0", "end")
            whitelist_text.insert("1.0", "\n".join(DEFAULT_BOZO_M_WHITELIST))

        btn_row = tk.Frame(frame, bg=BG)
        btn_row.pack(side="bottom", fill="x", pady=(16, 0))
        tk.Button(
            btn_row, text="Save",
            font=("Helvetica", 13, "bold"),
            bg=ACCENT, fg="#0a0a0a", activebackground="#16a34a",
            relief="flat", padx=16, pady=8, cursor="hand2",
            command=save,
        ).pack(side="right")
        self._text_button(
            btn_row, "Reset to defaults", reset,
            font=("Helvetica", 11), padx=12, pady=6,
        ).pack(side="right", padx=(0, 10))
