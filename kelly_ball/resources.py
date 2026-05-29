"""Discovery of bundled resource files for the audio subsystem.

The intro-image lookup (``find_intro_image``) lives in
``kelly_ball/__init__.py`` so that tests can monkeypatch ``_resource_dir``
on the ``kelly_ball`` namespace and have the patched value take effect.
This module covers everything else.
"""
import sys
from pathlib import Path

from .theme import EXTERNAL_RESOURCE_DIR


def _resource_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def find_bundled_audio(names: tuple[str, ...]) -> Path | None:
    for base in (_resource_dir(), EXTERNAL_RESOURCE_DIR):
        for name in names:
            p = base / name
            if p.exists():
                return p
    return None
