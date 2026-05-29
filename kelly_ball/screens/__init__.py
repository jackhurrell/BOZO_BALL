"""Per-screen mixin classes that compose into `KellyBallApp`."""
from .champion import ChampionMixin
from .reveal import RevealMixin
from .settings import SettingsMixin
from .setup import SetupMixin
from .splash import SplashMixin
from .stats import StatsMixin
from .summary import SummaryMixin

__all__ = [
    "ChampionMixin",
    "RevealMixin",
    "SettingsMixin",
    "SetupMixin",
    "SplashMixin",
    "StatsMixin",
    "SummaryMixin",
]
