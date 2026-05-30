"""Bridge-level tests for the pywebview Api wrapper (no GUI)."""
import pytest

from kelly_ball.api import Api


@pytest.fixture
def app(tmp_path):
    return Api(roster_path=tmp_path / "r.json", settings_path=tmp_path / "s.json")


def test_bootstrap_shape(app):
    boot = app.get_bootstrap()
    assert boot["max_players"] == 15
    assert boot["ball_colors"]["8"] == "#111111"      # string keys for JSON
    assert boot["ball_colors"]["1"] == "#f5c518"
    assert set(boot["palette"]) >= {"bg", "fg", "accent", "bozo"}
    assert "settings" in boot and "recents" in boot
    assert boot["settings"]["intro_enabled"] is True   # cinematic intro on by default


def test_start_draw_error_is_returned_not_raised(app):
    assert "error" in app.start_draw([])


def test_full_flow_to_summary_and_winner(app):
    st = app.start_draw(["Ann", "Morgan", "Bob"], False)
    assert st["view"] == "reveal"
    for _ in range(12):
        st = app.advance_reveal()
        if st.get("view") == "summary":
            break
    assert st["view"] == "summary" and len(st["players"]) == 3
    assert app.toggle_winner("Ann") == {"name": "Ann", "winner": True}
    assert app.toggle_winner("Ann") == {"name": "Ann", "winner": False}


def test_bozo_flash_flag_for_m_name(app):
    app.start_draw(["Morgan"], False)
    app.advance_reveal()
    st = app.reveal_state()
    assert st["display_name"] == "BOZO Morgan" and st["show_bozo_flash"] is True


def test_next_round_requires_winner(app):
    app.start_draw(["Ann", "Bob"], True)
    assert "error" in app.next_round()


def test_forget_all_clears_recents(app):
    app.start_draw(["Ann", "Bob"], False)
    assert len(app.recents()) == 2
    assert app.forget_all() == {"forgotten": 2}
    assert app.recents() == []


def test_save_settings_roundtrip(app):
    s = app.save_settings({"bozo_enabled": False})
    assert s["bozo_enabled"] is False
    assert app.display_name("Morgan") == "Morgan"


def test_intro_enabled_toggle_roundtrip(app):
    s = app.save_settings({"intro_enabled": False})
    assert s["intro_enabled"] is False
    assert app.get_bootstrap()["settings"]["intro_enabled"] is False
