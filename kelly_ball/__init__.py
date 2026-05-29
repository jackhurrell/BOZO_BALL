"""BOZO Ball — Kelly pool order-of-play GUI.

The public surface preserved for tests (`test_kelly_ball.py`) and the
PyInstaller build is re-exported here so callers can keep using
``import kelly_ball`` / ``from kelly_ball import KellyBallApp``.

``_resource_dir``, ``EXTERNAL_RESOURCE_DIR``, and ``find_intro_image`` are
defined directly in this module (not just re-exported from ``resources``)
so the tests can monkeypatch them on the ``kelly_ball`` namespace and have
the patched values take effect when ``find_intro_image`` is called.
"""
import sys
from pathlib import Path
from tkinter import messagebox  # re-exported for tests that patch it

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
    """Search bundled resources, then the user's BOZO_RESOURCES folder.

    Looks up ``_resource_dir`` and ``EXTERNAL_RESOURCE_DIR`` through the
    module globals at call time so monkeypatch can swap them out in tests.
    """
    for base in (_resource_dir(), EXTERNAL_RESOURCE_DIR):
        for name in INTRO_FILENAMES:
            p = base / name
            if p.exists():
                return p
    return None


# Imported last because `.app` (via screens) pulls in `kelly_ball` lazily
# through late imports for resource lookup helpers defined above.
from .app import KellyBallApp  # noqa: E402

__all__ = [
    "ACCENT",
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
    "KellyBallApp",
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
    "messagebox",
    "save_roster",
    "save_settings",
]
