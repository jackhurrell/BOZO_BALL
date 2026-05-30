"""Logic tests for the framework-free GameController (no GUI)."""
import json
from pathlib import Path

import pytest

from kelly_ball.core import GameController
from kelly_ball.theme import MAX_PLAYERS


@pytest.fixture
def game(tmp_path):
    return GameController(
        roster_path=tmp_path / "roster.json",
        settings_path=tmp_path / "settings.json",
    )


# ---- Draw ------------------------------------------------------------
def test_draw_assigns_unique_balls_in_range(game):
    names = ["Ann", "Bob", "Cy", "Dot", "Eve"]
    state = game.start_draw(names)
    balls = [b for _, b in game.assignments]
    assert len(balls) == len(names)
    assert len(set(balls)) == len(balls)
    assert all(1 <= b <= MAX_PLAYERS for b in balls)
    assert [n for n, _ in game.assignments] == names
    assert state["view"] == "reveal" and state["stage"] == "name"


def test_draw_rejects_empty(game):
    with pytest.raises(ValueError):
        game.start_draw([])
    with pytest.raises(ValueError):
        game.start_draw(["   "])


def test_draw_rejects_too_many(game):
    with pytest.raises(ValueError):
        game.start_draw([f"P{i}" for i in range(MAX_PLAYERS + 1)])


def test_draw_allows_exactly_max(game):
    game.start_draw([f"P{i}" for i in range(MAX_PLAYERS)])
    assert len(game.assignments) == MAX_PLAYERS


def test_draw_updates_roster_games_and_enabled(game):
    game.start_draw(["Ann", "Bob"])
    by = {e["name"]: e for e in game.roster}
    assert by["Ann"]["games"] == 1 and by["Ann"]["enabled"] is True
    game.start_draw(["Ann"])
    by = {e["name"]: e for e in game.roster}
    assert by["Ann"]["games"] == 2 and by["Bob"]["enabled"] is False


# ---- Reveal state machine -------------------------------------------
def test_reveal_progression(game):
    game.start_draw(["Ann", "Bob"])
    assert game.reveal_state()["stage"] == "name"
    assert game.advance_reveal()["stage"] == "ball"
    s = game.advance_reveal()
    assert s["stage"] == "name" and s["index"] == 1
    assert game.advance_reveal()["stage"] == "ball"
    assert game.advance_reveal()["view"] == "summary"


# ---- BOZO prank ------------------------------------------------------
def test_bozo_rule(game):
    assert game.display_name("Morgan") == "BOZO Morgan"
    assert game.display_name("Mark") == "Mark"
    assert game.display_name("Ann") == "Ann"


def test_bozo_disabled(game):
    game.update_settings({"bozo_enabled": False})
    assert game.display_name("Morgan") == "Morgan"


def test_reveal_flash_decision(game):
    game.start_draw(["Morgan"])
    game.advance_reveal()
    st = game.reveal_state()
    assert st["is_bozo"] is True and st["show_bozo_flash"] is True
    game.mark_bozo_flash_shown()
    assert game.reveal_state()["show_bozo_flash"] is False


# ---- Winners + tournament -------------------------------------------
def test_record_and_unmark_winner_persists(game):
    game.start_draw(["Ann", "Bob"])
    game.record_winner("Ann")
    assert "Ann" in game.current_winners
    assert next(e for e in game.roster if e["name"] == "Ann")["wins"] == 1
    game.unmark_winner("Ann")
    assert "Ann" not in game.current_winners
    assert next(e for e in game.roster if e["name"] == "Ann")["wins"] == 0


def test_can_advance_validation(game):
    game.start_draw(["Ann", "Bob"])
    ok, msg = game.can_advance()
    assert not ok and "winner" in msg.lower()
    game.record_winner("Ann")
    game.record_winner("Bob")
    ok, msg = game.can_advance()
    assert not ok and "loser" in msg.lower()


def test_tournament_reduces_to_champion(game):
    game.start_draw(["Ann", "Bob", "Cy", "Dot"], tournament=True)
    assert game.tournament_round == 1
    game.record_winner("Ann")
    game.record_winner("Bob")
    nxt = game.next_tournament_round()
    assert nxt["view"] == "reveal" and game.tournament_round == 2
    assert {n for n, _ in game.assignments} == {"Ann", "Bob"}
    game.record_winner("Ann")
    champ = game.next_tournament_round()
    assert champ["view"] == "champion" and champ["name"] == "Ann"


# ---- Forget / clear recents -----------------------------------------
def test_forget_all_clears_roster(game):
    game.start_draw(["Ann", "Bob", "Cy"])
    assert len(game.roster) == 3
    assert game.forget_all() == 3
    assert game.roster == []
    assert game.recents() == []
    assert game.forget_all() == 0


# ---- Late join -------------------------------------------------------
def test_late_join_gets_unused_ball(game):
    game.start_draw(["Ann"])
    used = {b for _, b in game.assignments}
    ball = game.add_late_player("Zed")
    assert ball is not None and ball not in used
    assert len(game.assignments) == 2


def test_late_join_rejects_duplicate(game):
    game.start_draw(["Ann"])
    assert game.add_late_player("ann") is None


# ---- Persistence -----------------------------------------------------
def test_roster_persists_across_instances(tmp_path):
    rp, sp = tmp_path / "roster.json", tmp_path / "settings.json"
    g1 = GameController(roster_path=rp, settings_path=sp)
    g1.start_draw(["Ann"])
    g1.record_winner("Ann")
    g2 = GameController(roster_path=rp, settings_path=sp)
    ann = next(e for e in g2.roster if e["name"] == "Ann")
    assert ann["wins"] == 1 and ann["games"] == 1


def test_settings_update_persists(tmp_path):
    sp = tmp_path / "settings.json"
    g = GameController(roster_path=tmp_path / "r.json", settings_path=sp)
    g.update_settings({"bozo_enabled": False, "whitelist": ["foo", " "]})
    saved = json.loads(Path(sp).read_text())
    assert saved["bozo_enabled"] is False and saved["whitelist"] == ["foo"]


def test_intro_enabled_defaults_true_and_persists(tmp_path):
    sp = tmp_path / "settings.json"
    g = GameController(roster_path=tmp_path / "r.json", settings_path=sp)
    assert g.settings["intro_enabled"] is True
    g.update_settings({"intro_enabled": False})
    assert json.loads(Path(sp).read_text())["intro_enabled"] is False
    g2 = GameController(roster_path=tmp_path / "r.json", settings_path=sp)
    assert g2.settings["intro_enabled"] is False


def test_stats_aggregate(game):
    game.start_draw(["Ann", "Bob"])
    game.record_winner("Ann")
    s = game.stats()
    assert s["players_known"] == 2 and s["total_wins"] == 1
    assert s["top_winners"][0]["name"] == "Ann"
