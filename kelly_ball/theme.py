"""Color palette, sizing, timing, and filename constants."""
from pathlib import Path


BALL_COLORS = {
    1: "#f5c518",   # yellow solid
    2: "#1f6feb",   # blue solid
    3: "#e5484d",   # red solid
    4: "#8b5cf6",   # purple solid
    5: "#f97316",   # orange solid
    6: "#16a34a",   # green solid
    7: "#7f1d1d",   # maroon/brown solid
    8: "#111111",   # black
    9: "#f5c518",   # yellow stripe
    10: "#1f6feb",  # blue stripe
    11: "#e5484d",  # red stripe
    12: "#8b5cf6",  # purple stripe
    13: "#f97316",  # orange stripe
    14: "#16a34a",  # green stripe
    15: "#7f1d1d",  # maroon stripe
}

BG = "#0f1115"
FG = "#f5f7fa"
ACCENT = "#22c55e"
MUTED = "#9aa3af"
PANEL = "#1a1d24"
LINE = "#2a2f3a"
DIM = "#5a6370"
DANGER = "#e5484d"
BOZO_YELLOW = "#fbbf24"
BOZO_TEXT_DARK = "#1f1408"

ROSTER_FILENAME = "roster.json"
SETTINGS_FILENAME = "settings.json"
ROSTER_DIR_NAME = ".bozo_ball"
MAX_PLAYERS = 15

CONFETTI_COLORS = (
    "#22c55e", "#fbbf24", "#e5484d", "#1f6feb",
    "#8b5cf6", "#f97316", "#f5c518",
)

DEFAULT_BOZO_M_WHITELIST = (
    "marcus", "markus", "marco", "marcos", "marc", "mark",
    "mitchell", "mitchel", "mitch",
)

DEFAULT_SETTINGS = {
    "bozo_enabled": True,
    "whitelist": list(DEFAULT_BOZO_M_WHITELIST),
    "background_music_enabled": True,
    # False = mode 1 (classic): name screen shows "BOZO <name>", then flash.
    # True  = mode 2 (surprise): name screen shows just "<name>", then text
    # animation + clown image flash before the ball reveal.
    "bozo_surprise_mode": False,
}

BOZO_FLASH_VISUAL_MS = 300  # mode 1: how long the clown image flashes on screen
BOZO_SURPRISE_TEXT_MS = 400  # mode 2: duration of "BOZO" + 🤡 pop-in animation
BOZO_SURPRISE_IMAGE_MS = 300  # mode 2: how long the clown image holds after the text

BACKGROUND_FADE_IN_S = 2.0
BACKGROUND_LOOP_GAP_MS = 250
BACKGROUND_WATCHDOG_MS = 400
BACKGROUND_RESUME_DELAY_MS = 150

INTRO_FILENAMES = ("intro.png", "intro.gif", "BOZO_IMAGE.png")
SPLASH_AUDIO_FILENAMES = ("splash.mp3", "splash.m4a", "splash.wav")
BACKGROUND_AUDIO_FILENAMES = (
    "background.mp3", "Background.mp3", "background.m4a", "background.wav",
)
EXTERNAL_RESOURCE_DIR = Path.home() / "Desktop" / "BOZO_RESOURCES"
