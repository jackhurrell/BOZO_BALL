"""Looping background music with duck/resume + watchdog respawn."""
import shutil
import subprocess
import sys
import tkinter as tk

from ..resources import find_bundled_audio
from ..theme import (
    BACKGROUND_AUDIO_FILENAMES,
    BACKGROUND_FADE_IN_S,
    BACKGROUND_RESUME_DELAY_MS,
    BACKGROUND_WATCHDOG_MS,
)
from .cache import ensure_trimmed_audio


class BackgroundMusic:
    """Persistent loop with duck/resume. Needs a Tk root for `after()`."""

    def __init__(self, root: tk.Misc, *, muted: bool | None = None) -> None:
        self._root = root
        self._proc: subprocess.Popen | None = None
        self._active: bool = False
        self._after_id: str | None = None
        self._resume_after_id: str | None = None
        # Auto-mute under pytest so test runs stay silent.
        self.muted = muted if muted is not None else "pytest" in sys.modules

    def start(self, *, with_fade_in: bool = True) -> None:
        """Begin looping. Idempotent if already active."""
        if self.muted:
            return
        if find_bundled_audio(BACKGROUND_AUDIO_FILENAMES) is None:
            return
        if shutil.which("afplay") is None:
            return
        self._active = True
        self._spawn_iteration(fade_in=with_fade_in)
        self._schedule_watchdog()

    def stop(self) -> None:
        """Disable the loop and terminate any current music process."""
        self._active = False
        self._cancel_after("_after_id")
        self._cancel_after("_resume_after_id")
        self._terminate_proc()

    def duck_for(self, hold_ms: int) -> None:
        """Stop the music for a foreground effect, then restart with fade-in."""
        if not self._active:
            return
        self._active = False
        self._cancel_after("_after_id")
        self._terminate_proc()
        self._cancel_after("_resume_after_id")
        self._resume_after_id = self._root.after(
            hold_ms + BACKGROUND_RESUME_DELAY_MS, self._resume,
        )

    def _resume(self) -> None:
        self._resume_after_id = None
        self.start(with_fade_in=True)

    def _spawn_iteration(self, *, fade_in: bool) -> None:
        src = find_bundled_audio(BACKGROUND_AUDIO_FILENAMES)
        if src is None:
            return
        afplay = shutil.which("afplay")
        if afplay is None:
            return
        path = src
        if fade_in:
            faded = ensure_trimmed_audio(
                src, 0.0, 60 * 60.0, fade_in_s=BACKGROUND_FADE_IN_S
            )
            if faded is not None:
                path = faded
        self._terminate_proc()
        try:
            self._proc = subprocess.Popen(
                [afplay, str(path)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except OSError:
            self._proc = None

    def _schedule_watchdog(self) -> None:
        self._cancel_after("_after_id")
        self._after_id = self._root.after(
            BACKGROUND_WATCHDOG_MS, self._watchdog_tick
        )

    def _watchdog_tick(self) -> None:
        self._after_id = None
        if not self._active:
            return
        proc = self._proc
        if proc is None or proc.poll() is not None:
            self._spawn_iteration(fade_in=False)
        self._schedule_watchdog()

    def _terminate_proc(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None or proc.poll() is not None:
            return
        try:
            proc.terminate()
        except OSError:
            pass

    def _cancel_after(self, attr: str) -> None:
        after_id = getattr(self, attr)
        if after_id is None:
            return
        try:
            self._root.after_cancel(after_id)
        except (ValueError, tk.TclError):
            pass
        setattr(self, attr, None)
