"""pywebview ⇆ JavaScript bridge.

An `Api` instance is handed to ``webview.create_window(..., js_api=Api())``.
Every method is callable from the front-end as
``await pywebview.api.<method>(...)`` and returns JSON-serializable data.
All game rules live in :class:`kelly_ball.core.GameController`; this class is
a thin, defensive wrapper that adapts those calls for the bridge.
"""
from __future__ import annotations

from pathlib import Path

from .core import GameController
from .theme import (
    ACCENT,
    BALL_COLORS,
    BG,
    BOZO_YELLOW,
    DANGER,
    DIM,
    FG,
    LINE,
    MAX_PLAYERS,
    MUTED,
    PANEL,
)


class Api:
    def __init__(
        self,
        roster_path: Path | None = None,
        settings_path: Path | None = None,
    ):
        self.game = GameController(
            roster_path=roster_path, settings_path=settings_path
        )

    # ---- Bootstrap ----------------------------------------------------
    def get_bootstrap(self) -> dict:
        return {
            "max_players": MAX_PLAYERS,
            # JSON object keys are strings, so key ball colours by str.
            "ball_colors": {str(k): v for k, v in BALL_COLORS.items()},
            "palette": {
                "bg": BG, "fg": FG, "accent": ACCENT, "muted": MUTED,
                "panel": PANEL, "line": LINE, "dim": DIM,
                "danger": DANGER, "bozo": BOZO_YELLOW,
            },
            "settings": dict(self.game.settings),
            "recents": self.game.recents(),
            "default_chips": self.game.default_chips(),
        }

    # ---- Setup / roster ----------------------------------------------
    def recents(self) -> list[dict]:
        return self.game.recents()

    def forget(self, name: str) -> bool:
        return self.game.forget(name)

    def forget_all(self) -> dict:
        return {"forgotten": self.game.forget_all()}

    def display_name(self, name: str) -> str:
        return self.game.display_name(name)

    # ---- Draw / reveal -----------------------------------------------
    def start_draw(self, names: list[str], tournament: bool = False) -> dict:
        try:
            return self.game.start_draw(names, tournament)
        except ValueError as exc:
            return {"error": str(exc)}

    def reveal_state(self) -> dict:
        return self.game.reveal_state()

    def advance_reveal(self) -> dict:
        return self.game.advance_reveal()

    def mark_bozo_flash_shown(self) -> None:
        self.game.mark_bozo_flash_shown()

    def cancel_draw(self) -> dict:
        self.game.cancel_draw()
        return {"ok": True}

    # ---- Summary / winners / tournament ------------------------------
    def summary_state(self) -> dict:
        return self.game.summary_state()

    def toggle_winner(self, name: str) -> dict:
        return {"name": name, "winner": self.game.toggle_winner(name)}

    def add_late_player(self, name: str) -> dict:
        ball = self.game.add_late_player(name)
        if ball is None:
            return {"error": "Could not add player (duplicate or table full)"}
        return {"name": name, "ball": ball, **self.game.summary_state()}

    def can_advance(self) -> dict:
        ok, msg = self.game.can_advance()
        return {"ok": ok, "message": msg}

    def next_round(self) -> dict:
        ok, msg = self.game.can_advance()
        if not ok:
            return {"error": msg}
        return self.game.next_tournament_round()

    # ---- Stats / settings --------------------------------------------
    def stats(self) -> dict:
        return self.game.stats()

    def save_settings(self, changes: dict) -> dict:
        return self.game.update_settings(changes)
