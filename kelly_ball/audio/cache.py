"""ffmpeg-backed trimmed audio cache, keyed on filename + mtime + offsets."""
import shutil
import subprocess
from pathlib import Path

from ..theme import ROSTER_DIR_NAME


def audio_cache_dir() -> Path:
    return Path.home() / ROSTER_DIR_NAME / "audio_cache"


def ensure_trimmed_audio(
    src: Path,
    start_s: float,
    duration_s: float,
    *,
    fade_out_s: float = 0.0,
    fade_in_s: float = 0.0,
) -> Path | None:
    """Extract a clip from `src` starting at `start_s` for `duration_s` seconds.

    Uses ffmpeg; result is cached so re-encoding only happens when inputs
    change. Returns None if ffmpeg is unavailable or extraction fails.
    """
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return None
    try:
        mtime = int(src.stat().st_mtime)
    except OSError:
        return None
    cache_dir = audio_cache_dir()
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    cache_path = cache_dir / (
        f"{src.stem}_s{start_s}_d{duration_s}"
        f"_fo{fade_out_s}_fi{fade_in_s}_m{mtime}.m4a"
    )
    if cache_path.exists():
        return cache_path
    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-ss", str(start_s), "-i", str(src),
        "-t", str(duration_s),
    ]
    filters = []
    if fade_in_s > 0:
        filters.append(f"afade=t=in:st=0:d={fade_in_s}")
    if fade_out_s > 0:
        fade_start = max(0.0, duration_s - fade_out_s)
        filters.append(f"afade=t=out:st={fade_start}:d={fade_out_s}")
    if filters:
        cmd += ["-af", ",".join(filters)]
    cmd += ["-vn", "-c:a", "aac", "-b:a", "192k", str(cache_path)]
    try:
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return cache_path if cache_path.exists() else None
