"""Framework-free game core.

`GameController` owns all BOZO Ball game state and rules with no Tkinter,
no pywebview, and no rendering dependency. The front-end (Three.js via
pywebview) drives this controller so the draw logic, tournament flow, BOZO
prank rule, and persistence stay in one authoritative place.
"""
from .game import GameController

__all__ = ["GameController"]
