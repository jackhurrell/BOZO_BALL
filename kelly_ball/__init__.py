"""BOZO Ball — Kelly pool order-of-play app (3D / pywebview front-end).

Game rules live in :class:`kelly_ball.core.GameController`; the JavaScript
front-end talks to them through :class:`kelly_ball.api.Api`. The pure helpers
(`display_name`, persistence, theme constants) are re-exported here for
convenience and for the test-suite.
"""
import sys
from pathlib import Path

from .display import _BOZO_M_WHITELIST, _interp_color, display_name
from .persistence import (
    default_roster_path,
    default_settings_path,
    load_roster,
    load_settings,
    save_roster,
    save_settings,
)
from .theme import (
    ACCENT,
    BALL_COLORS,
    BG,
    BOZO_TEXT_DARK,
    BOZO_YELLOW,
    CONFETTI_COLORS,
    DANGER,
    DEFAULT_BOZO_M_WHITELIST,
    DEFAULT_SETTINGS,
    DIM,
    EXTERNAL_RESOURCE_DIR,
    FG,
    INTRO_FILENAMES,
    LINE,
    MAX_PLAYERS,
    MUTED,
    PANEL,
)


def _resource_dir() -> Path:
    """Where bundled resources live, in dev or in a PyInstaller app."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def find_intro_image() -> Path | None:
    """Search bundled resources, then the user's BOZO_RESOURCES folder."""
    for base in (_resource_dir(), EXTERNAL_RESOURCE_DIR):
        for name in INTRO_FILENAMES:
            p = base / name
            if p.exists():
                return p
    return None


# Imported after the helpers so the bridge/controller can rely on them.
from .api import Api  # noqa: E402
from .core import GameController  # noqa: E402

__all__ = [
    "ACCENT",
    "Api",
    "BALL_COLORS",
    "BG",
    "BOZO_TEXT_DARK",
    "BOZO_YELLOW",
    "CONFETTI_COLORS",
    "DANGER",
    "DEFAULT_BOZO_M_WHITELIST",
    "DEFAULT_SETTINGS",
    "DIM",
    "EXTERNAL_RESOURCE_DIR",
    "FG",
    "GameController",
    "INTRO_FILENAMES",
    "LINE",
    "MAX_PLAYERS",
    "MUTED",
    "PANEL",
    "_BOZO_M_WHITELIST",
    "_interp_color",
    "_resource_dir",
    "default_roster_path",
    "default_settings_path",
    "display_name",
    "find_intro_image",
    "load_roster",
    "load_settings",
    "save_roster",
    "save_settings",
]
