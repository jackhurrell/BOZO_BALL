"""Audio subsystem: foreground (one-shot) and background (looped) playback."""
from .background import BackgroundMusic
from .cache import audio_cache_dir, ensure_trimmed_audio
from .foreground import ForegroundAudio

__all__ = [
    "BackgroundMusic",
    "ForegroundAudio",
    "audio_cache_dir",
    "ensure_trimmed_audio",
]
