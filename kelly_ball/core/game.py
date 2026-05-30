"""`GameController` — all BOZO Ball game state and rules, framework-free.

A direct port of the logic that previously lived inside the Tkinter screen
mixins (``screens/setup.py``, ``screens/reveal.py``, ``screens/summary.py``,
``screens/stats.py``). Nothing here imports tkinter or any rendering library;
methods return plain JSON-serializable data so a front-end (Three.js via
pywebview, or anything else) can render while the rules stay in Python.
"""
from __future__ import annotations

import random
from datetime import date
from pathlib import Path

from ..display import display_name
from ..persistence import (
    default_roster_path,
    default_settings_path,
    load_roster,
    load_settings,
    save_roster,
    save_settings,
)
from ..theme import DEFAULT_BOZO_M_WHITELIST, MAX_PLAYERS


class GameController:
    """Owns roster, settings, and the state of an in-progress draw.

    The reveal flow is a small state machine so the front-end only asks
    "what should I show next?" rather than re-implementing the
    name→ball→next-player progression.
    """

    def __init__(
        self,
        roster_path: Path | None = None,
        settings_path: Path | None = None,
    ):
        self.roster_path: Path = roster_path or default_roster_path()
        self.settings_path: Path = settings_path or default_settings_path()
        self.roster: list[dict] = load_roster(self.roster_path)
        self.settings: dict = load_settings(self.settings_path)

        # In-progress draw state.
        self.assignments: list[tuple[str, int]] = []
        self.reveal_index: int = 0
        self.reveal_stage: str = "name"  # "name" | "ball"
        self.last_names: list[str] = []
        self.current_winners: set[str] = set()
        self.tournament_mode: bool = False
        self.tournament_round: int = 0
        # Per-player guard so the BOZO flash only fires once per reveal.
        self._bozo_flash_done: bool = False

    # ------------------------------------------------------------------
    # Display-name (the BOZO prank) — single source of truth.
    # ------------------------------------------------------------------
    def display_name(self, name: str) -> str:
        return display_name(
            name,
            enabled=bool(self.settings.get("bozo_enabled", True)),
            whitelist=frozenset(
                s.lower()
                for s in self.settings.get("whitelist", DEFAULT_BOZO_M_WHITELIST)
            ),
        )

    def is_surprise_mode(self) -> bool:
        return bool(self.settings.get("bozo_surprise_mode", False))

    # ------------------------------------------------------------------
    # Setup / recents / roster maintenance.
    # ------------------------------------------------------------------
    def recents(self) -> list[dict]:
        """Roster entries sorted for the "recently played" tray."""
        ordered = sorted(
            self.roster,
            key=lambda e: (e.get("last_played", ""), e.get("games", 0)),
            reverse=True,
        )
        return [
            {
                "name": e["name"],
                "wins": int(e.get("wins", 0)),
                "games": int(e.get("games", 0)),
                "last_played": e.get("last_played", ""),
            }
            for e in ordered
        ]

    def default_chips(self) -> list[str]:
        """Names to pre-fill the tray with: last game (rematch) or enabled."""
        if self.last_names:
            return list(self.last_names)
        return [e["name"] for e in self.roster if e.get("enabled")]

    def forget(self, name: str) -> bool:
        before = len(self.roster)
        self.roster = [
            e for e in self.roster if e["name"].lower() != name.lower()
        ]
        if len(self.roster) != before:
            save_roster(self.roster_path, self.roster)
            return True
        return False

    def forget_all(self) -> int:
        """Clear the entire roster cache; returns how many were forgotten."""
        count = len(self.roster)
        if count:
            self.roster = []
            save_roster(self.roster_path, self.roster)
        return count

    # ------------------------------------------------------------------
    # Draw — assign a unique ball (1..15) to each player.
    # ------------------------------------------------------------------
    def start_draw(self, names: list[str], tournament: bool = False) -> dict:
        """Begin a new draw. Ported from ``screens/setup.py:start_draw``."""
        names = [n.strip() for n in names if n and n.strip()]
        if not names:
            raise ValueError("Add at least one player to start")
        if len(names) > MAX_PLAYERS:
            raise ValueError(
                f"Max {MAX_PLAYERS} players — Kelly pool only has 15 balls"
            )

        today = date.today().isoformat()
        by_key = {e["name"].lower(): e for e in self.roster}
        chip_keys = {n.lower() for n in names}
        for n in names:
            key = n.lower()
            if key in by_key:
                entry = by_key[key]
                entry["last_played"] = today
                entry["games"] = int(entry.get("games", 0)) + 1
                entry["enabled"] = True
            else:
                entry = {
                    "name": n, "last_played": today,
                    "games": 1, "wins": 0, "enabled": True,
                }
                self.roster.append(entry)
                by_key[key] = entry
        for entry in self.roster:
            if entry["name"].lower() not in chip_keys:
                entry["enabled"] = False
        save_roster(self.roster_path, self.roster)

        balls = random.sample(range(1, MAX_PLAYERS + 1), len(names))
        self.assignments = list(zip(names, balls))
        self.last_names = list(names)
        self.current_winners = set()
        self.tournament_mode = bool(tournament)
        self.tournament_round = 1 if tournament else 0
        self.reveal_index = 0
        self.reveal_stage = "name"
        self._bozo_flash_done = False
        return self.reveal_state()

    # ------------------------------------------------------------------
    # Reveal state machine.
    # ------------------------------------------------------------------
    def reveal_state(self) -> dict:
        """Describe what the front-end should currently show."""
        if self.reveal_index >= len(self.assignments):
            return {"view": "summary", **self.summary_state()}

        name, ball = self.assignments[self.reveal_index]
        bozo = self.display_name(name) != name
        shown_name = name if self.is_surprise_mode() else self.display_name(name)
        return {
            "view": "reveal",
            "stage": self.reveal_stage,
            "index": self.reveal_index,
            "total": len(self.assignments),
            "name": name,
            "shown_name": shown_name,
            "display_name": self.display_name(name),
            "ball": ball,
            "is_bozo": bozo,
            "surprise_mode": self.is_surprise_mode(),
            "show_bozo_flash": (
                self.reveal_stage == "ball" and bozo and not self._bozo_flash_done
            ),
            "tournament_mode": self.tournament_mode,
            "tournament_round": self.tournament_round,
        }

    def mark_bozo_flash_shown(self) -> None:
        self._bozo_flash_done = True

    def advance_reveal(self) -> dict:
        """name → ball (same player) → name (next player) → … → summary."""
        if self.reveal_stage == "name":
            self.reveal_stage = "ball"
            self._bozo_flash_done = False  # arm the flash for this player
            return self.reveal_state()

        self.reveal_index += 1
        self.reveal_stage = "name"
        self._bozo_flash_done = False
        return self.reveal_state()

    def cancel_draw(self) -> None:
        self.assignments = []
        self.reveal_index = 0
        self.reveal_stage = "name"
        self._bozo_flash_done = False
        self.current_winners = set()
        self.tournament_round = 0

    # ------------------------------------------------------------------
    # Summary / winners / late join.
    # ------------------------------------------------------------------
    def summary_state(self) -> dict:
        used = {b for _, b in self.assignments}
        return {
            "tournament_mode": self.tournament_mode,
            "tournament_round": self.tournament_round,
            "can_late_join": len(used) < MAX_PLAYERS,
            "players": [
                {
                    "name": name,
                    "display_name": self.display_name(name),
                    "ball": ball,
                    "winner": name in self.current_winners,
                }
                for name, ball in self.assignments
            ],
        }

    def record_winner(self, name: str) -> None:
        """Mark a winner and bump their persistent win count."""
        if name in self.current_winners:
            return
        key = name.lower()
        for entry in self.roster:
            if entry["name"].lower() == key:
                entry["wins"] = int(entry.get("wins", 0)) + 1
                break
        else:
            self.roster.append({
                "name": name, "last_played": date.today().isoformat(),
                "games": 1, "wins": 1, "enabled": True,
            })
        self.current_winners.add(name)
        save_roster(self.roster_path, self.roster)

    def unmark_winner(self, name: str) -> None:
        if name not in self.current_winners:
            return
        self.current_winners.discard(name)
        for entry in self.roster:
            if entry["name"].lower() == name.lower():
                entry["wins"] = max(0, int(entry.get("wins", 0)) - 1)
                break
        save_roster(self.roster_path, self.roster)

    def toggle_winner(self, name: str) -> bool:
        """Flip a player's winner state; returns the new state."""
        if name in self.current_winners:
            self.unmark_winner(name)
            return False
        self.record_winner(name)
        return True

    def add_late_player(self, name: str) -> int | None:
        """Add a post-draw player with a random unused ball.

        Returns the assigned ball, or None if rejected (dup / table full).
        """
        name = name.strip()
        if not name:
            return None
        existing = {n.lower() for n, _ in self.assignments}
        if name.lower() in existing:
            return None
        used = {b for _, b in self.assignments}
        available = [b for b in range(1, MAX_PLAYERS + 1) if b not in used]
        if not available:
            return None
        ball = random.choice(available)
        self.assignments.append((name, ball))
        self.last_names.append(name)

        today = date.today().isoformat()
        key = name.lower()
        for entry in self.roster:
            if entry["name"].lower() == key:
                entry["last_played"] = today
                entry["games"] = int(entry.get("games", 0)) + 1
                entry["enabled"] = True
                break
        else:
            self.roster.append({
                "name": name, "last_played": today,
                "games": 1, "wins": 0, "enabled": True,
            })
        save_roster(self.roster_path, self.roster)
        return ball

    # ------------------------------------------------------------------
    # Tournament progression.
    # ------------------------------------------------------------------
    def winners_this_round(self) -> list[str]:
        return [n for n, _ in self.assignments if n in self.current_winners]

    def can_advance(self) -> tuple[bool, str]:
        winners = self.winners_this_round()
        if not winners:
            return False, "Tap 🏆 to mark at least one winner"
        if len(winners) == len(self.assignments):
            return False, "Need at least one loser to advance"
        return True, ""

    def next_tournament_round(self, advancing: list[str] | None = None) -> dict:
        """Start the next round with the advancing players.

        Returns a "champion" view when ≤1 player remains, else a fresh
        "reveal" view for the next round.
        """
        if advancing is None:
            advancing = self.winners_this_round()

        if len(advancing) < 2:
            champ = advancing[0] if advancing else None
            return {
                "view": "champion",
                "name": champ,
                "display_name": self.display_name(champ) if champ else None,
            }

        self.tournament_round += 1
        save_roster(self.roster_path, self.roster)
        balls = random.sample(range(1, MAX_PLAYERS + 1), len(advancing))
        self.assignments = list(zip(advancing, balls))
        self.last_names = list(advancing)
        self.current_winners = set()
        self.reveal_index = 0
        self.reveal_stage = "name"
        self._bozo_flash_done = False
        return self.reveal_state()

    # ------------------------------------------------------------------
    # Stats / settings.
    # ------------------------------------------------------------------
    def stats(self) -> dict:
        def top(key: str) -> list[dict]:
            ranked = sorted(
                self.roster, key=lambda e: int(e.get(key, 0)), reverse=True
            )[:5]
            return [
                {"name": e["name"], "display_name": self.display_name(e["name"]),
                 "value": int(e.get(key, 0))}
                for e in ranked if int(e.get(key, 0)) > 0
            ]

        return {
            "players_known": len(self.roster),
            "total_appearances": sum(int(e.get("games", 0)) for e in self.roster),
            "total_wins": sum(int(e.get("wins", 0)) for e in self.roster),
            "top_winners": top("wins"),
            "most_games": top("games"),
        }

    def update_settings(self, changes: dict) -> dict:
        """Validate + persist a partial settings update; returns full settings."""
        if isinstance(changes.get("bozo_enabled"), bool):
            self.settings["bozo_enabled"] = changes["bozo_enabled"]
        if isinstance(changes.get("bozo_surprise_mode"), bool):
            self.settings["bozo_surprise_mode"] = changes["bozo_surprise_mode"]
        if isinstance(changes.get("background_music_enabled"), bool):
            self.settings["background_music_enabled"] = changes[
                "background_music_enabled"
            ]
        if isinstance(changes.get("intro_enabled"), bool):
            self.settings["intro_enabled"] = changes["intro_enabled"]
        wl = changes.get("whitelist")
        if isinstance(wl, list):
            self.settings["whitelist"] = [
                s for s in wl if isinstance(s, str) and s.strip()
            ]
        save_settings(self.settings_path, self.settings)
        return dict(self.settings)
