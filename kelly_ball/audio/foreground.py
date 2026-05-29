"""Fire-and-forget foreground audio (splash / flash effects) via afplay."""
import shutil
import subprocess
import sys

from ..resources import find_bundled_audio
from .cache import ensure_trimmed_audio


class ForegroundAudio:
    """One channel of one-shot playback. Calling `play` cancels any prior clip."""

    def __init__(self, *, muted: bool | None = None) -> None:
        self._proc: subprocess.Popen | None = None
        # Auto-mute under pytest so test runs stay silent; explicit muted=
        # overrides for callers that want to force one behaviour.
        self.muted = muted if muted is not None else "pytest" in sys.modules

    def play(
        self,
        names: tuple[str, ...],
        *,
        max_seconds: float | None = None,
        start_seconds: float = 0.0,
        fade_out_s: float = 0.0,
    ) -> None:
        """Silently no-op if muted, afplay is missing, or no file is bundled.

        When start_seconds > 0 or fade_out_s > 0, ffmpeg is used to pre-bake
        a cached clip (afplay can't seek or fade live); if ffmpeg is
        unavailable in those cases, playback is skipped.
        """
        if self.muted:
            return
        path = find_bundled_audio(names)
        if path is None:
            return
        afplay = shutil.which("afplay")
        if afplay is None:
            return
        needs_ffmpeg = start_seconds > 0 or fade_out_s > 0
        if needs_ffmpeg:
            trimmed = ensure_trimmed_audio(
                path,
                start_seconds,
                max_seconds or 60.0,
                fade_out_s=fade_out_s,
            )
            if trimmed is None:
                return
            path = trimmed
        self.stop()
        cmd = [afplay]
        if max_seconds is not None and not needs_ffmpeg:
            cmd += ["-t", str(max_seconds)]
        cmd.append(str(path))
        try:
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except OSError:
            self._proc = None

    def stop(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None or proc.poll() is not None:
            return
        try:
            proc.terminate()
        except OSError:
            pass
