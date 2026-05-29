"""Main `KellyBallApp` — state, lifecycle, and composed screen mixins."""
import tkinter as tk
from pathlib import Path

from .audio import BackgroundMusic, ForegroundAudio
from .persistence import (
    default_roster_path,
    default_settings_path,
    load_roster,
    load_settings,
)
from .screens import (
    ChampionMixin,
    RevealMixin,
    SettingsMixin,
    SetupMixin,
    SplashMixin,
    StatsMixin,
    SummaryMixin,
)
from .screens.base import ScreenHelpersMixin
from .theme import BG


class KellyBallApp(
    SplashMixin,
    SetupMixin,
    RevealMixin,
    SummaryMixin,
    StatsMixin,
    SettingsMixin,
    ChampionMixin,
    ScreenHelpersMixin,
    tk.Tk,
):
    def __init__(self, show_splash_on_start: bool = True,
                 roster_path: Path | None = None,
                 settings_path: Path | None = None):
        super().__init__()
        self.title("BOZO Ball")
        self.geometry("760x560")
        self.configure(bg=BG)
        self.minsize(640, 480)

        # Game state
        self.assignments: list[tuple[str, int]] = []
        self.reveal_index = 0
        self.reveal_stage = "name"  # "name" or "ball"
        self.last_names: list[str] = []
        # Names marked as winners this round; cleared at the start of each draw.
        self.current_winners: set[str] = set()

        # Tournament mode state
        self.tournament_mode: bool = False
        self.tournament_round: int = 0

        # Persistence + chip-tray state
        self.roster_path: Path = roster_path or default_roster_path()
        self.settings_path: Path = settings_path or default_settings_path()
        self.roster: list[dict] = load_roster(self.roster_path)
        self.settings: dict = load_settings(self.settings_path)
        self.current_chips: list[str] = []
        self._chip_widgets: dict[str, tk.Widget] = {}
        self._tray_outer: tk.Frame | None = None
        self._chips_row: tk.Frame | None = None
        self._recents_frame: tk.Frame | None = None
        self._count_label: tk.Label | None = None
        self._status_label: tk.Label | None = None
        self._status_after_id: str | None = None
        self._start_btn: tk.Button | None = None
        self.input_entry: tk.Entry | None = None
        self._placeholder_shown = False

        # Splash state
        self._splash_phase = "idle"
        self._splash_canvas = None
        self._splash_glyphs: list[dict] = []
        self._splash_subtitle = None
        self._splash_tick_count = 0
        self._splash_active_idx = 0
        self._splash_skip_binding = None

        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill="both", expand=True)

        # PhotoImage kept alive so Tk doesn't GC it before render.
        self._intro_image = None
        # Per-player flag: True after the BOZO flash has shown for this
        # player so it only plays once per reveal.
        self._bozo_flash_done = False
        # Reveal screen's Next button — the ball animation disables it until
        # the ball settles.
        self._next_btn: tk.Button | None = None

        # Two audio channels — foreground (splash / flash effects) and the
        # looping background music. Keeping them separate means the music
        # respawn watchdog doesn't fire on every short effect ending.
        self.fg_audio = ForegroundAudio()
        self.bg_music = BackgroundMusic(self)

        try:
            self.protocol("WM_DELETE_WINDOW", self._on_app_close)
        except tk.TclError:
            pass

        if show_splash_on_start:
            self.show_splash()
        else:
            self.show_setup()
            # No splash to fade out of — start the bg music right away.
            if self.settings.get("background_music_enabled", True):
                self.bg_music.start(with_fade_in=True)

    def clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def _on_app_close(self) -> None:
        """Window close handler — delegates to destroy() for unified cleanup."""
        try:
            self.destroy()
        except tk.TclError:
            pass

    def destroy(self):
        """Override Tk.destroy so audio is always cleaned up.

        Tests call ``instance.destroy()`` directly in fixture teardown
        (skipping ``_on_app_close``), so any cleanup that only lived there
        would leave afplay subprocesses outliving the test run.
        """
        try:
            self.bg_music.stop()
        except Exception:
            pass
        try:
            self.fg_audio.stop()
        except Exception:
            pass
        super().destroy()
