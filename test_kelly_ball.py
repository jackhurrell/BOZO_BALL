"""Tests for kelly_ball.py.

The app is a Tk GUI, so tests construct a hidden root window and drive the
public methods directly. messagebox is monkey-patched to capture warnings
instead of popping up dialogs. Each test gets a freshly constructed app via
the `app` fixture, and the whole suite is skipped if Tk cannot initialize
(e.g. running headless without a display).
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

tk = pytest.importorskip("tkinter")

import kelly_ball  # noqa: E402
from kelly_ball import (  # noqa: E402
    BALL_COLORS, KellyBallApp, display_name, load_roster, save_roster,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def warnings_log(monkeypatch):
    """Capture messagebox.showwarning calls instead of opening dialogs."""
    calls: list[tuple[str, str]] = []

    def _capture(title, message, *_a, **_kw):
        calls.append((title, message))

    monkeypatch.setattr(kelly_ball.messagebox, "showwarning", _capture)
    monkeypatch.setattr(
        kelly_ball.messagebox, "showerror", _capture, raising=False
    )
    monkeypatch.setattr(
        kelly_ball.messagebox, "showinfo", _capture, raising=False
    )
    return calls


@pytest.fixture
def app(warnings_log, tmp_path):
    """Construct a hidden KellyBallApp instance, tear it down after the test.

    Splash screen is skipped so tests land directly on the setup screen.
    Each test gets its own roster + settings file under tmp_path so the
    user's real ~/.bozo_ball/ is never touched.
    """
    try:
        instance = KellyBallApp(
            show_splash_on_start=False,
            roster_path=tmp_path / "roster.json",
            settings_path=tmp_path / "settings.json",
        )
    except tk.TclError as exc:
        pytest.skip(f"Tk unavailable in this environment: {exc}")
    instance.withdraw()
    try:
        yield instance
    finally:
        try:
            instance.destroy()
        except tk.TclError:
            pass


@pytest.fixture
def splash_app(warnings_log, tmp_path):
    """An app that boots into the splash screen — used for splash tests."""
    try:
        instance = KellyBallApp(
            show_splash_on_start=True,
            roster_path=tmp_path / "roster.json",
            settings_path=tmp_path / "settings.json",
        )
    except tk.TclError as exc:
        pytest.skip(f"Tk unavailable in this environment: {exc}")
    instance.update_idletasks()
    instance.withdraw()
    try:
        yield instance
    finally:
        try:
            instance.destroy()
        except tk.TclError:
            pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _enter_names(app: KellyBallApp, names) -> None:
    """Populate the chip tray with the given names.

    Accepts either a list of names or a single newline-delimited string for
    legacy callers. Empty / whitespace-only entries are skipped, matching the
    chip-input model where the entry widget strips on submit.
    """
    if isinstance(names, str):
        items = [n.strip() for n in names.splitlines() if n.strip()]
    else:
        items = [n.strip() for n in names if isinstance(n, str) and n.strip()]
    # Start from a clean tray
    app.current_chips = []
    if app._chips_row is not None:
        app._render_chips()
        app._update_footer()
    for n in items:
        app.add_chip(n)


def _run_full_reveal(app: KellyBallApp) -> None:
    """Click through name → ball for every player until the summary appears."""
    total = len(app.assignments)
    # 2 advances per player (name → ball, ball → next)
    for _ in range(total * 2):
        app.advance_reveal()


def _find_text_labels(widget) -> list[str]:
    """Recursively collect the `text` of every Label under `widget`."""
    out: list[str] = []
    for child in widget.winfo_children():
        if isinstance(child, tk.Label):
            try:
                out.append(child.cget("text"))
            except tk.TclError:
                pass
        out.extend(_find_text_labels(child))
    return out


# ---------------------------------------------------------------------------
# Constants & module-level invariants
# ---------------------------------------------------------------------------


class TestBallColors:
    def test_has_exactly_15_balls(self):
        assert set(BALL_COLORS.keys()) == set(range(1, 16))

    def test_every_color_is_hex(self):
        for ball, color in BALL_COLORS.items():
            assert isinstance(color, str), ball
            assert color.startswith("#") and len(color) == 7, (ball, color)


# ---------------------------------------------------------------------------
# Setup screen / start_draw validation
# ---------------------------------------------------------------------------


class TestStartDrawValidation:
    def test_no_chips_does_not_advance(self, app):
        # With the chip-input model the Start button is disabled when empty;
        # calling start_draw() directly should still no-op gracefully.
        app.current_chips = []
        app.start_draw()
        assert app.assignments == []

    def test_add_chip_caps_at_fifteen(self, app):
        # The cap is enforced at chip-add time, not at start_draw.
        for i in range(20):
            app.add_chip(f"P{i}")
        assert len(app.current_chips) == 15

    def test_start_button_disabled_when_empty(self, app):
        app.current_chips = []
        app._update_footer()
        assert app._start_btn.cget("state") == "disabled"

    def test_start_button_enabled_with_chips(self, app):
        app.add_chip("Alice")
        assert app._start_btn.cget("state") == "normal"

    @pytest.mark.parametrize("count", [1, 2, 8, 14, 15])
    def test_valid_counts_advance(self, app, count):
        _enter_names(app, [f"Player {i + 1}" for i in range(count)])
        app.start_draw()
        assert len(app.assignments) == count
        assert app.reveal_index == 0
        assert app.reveal_stage == "name"


# ---------------------------------------------------------------------------
# Name parsing edge cases
# ---------------------------------------------------------------------------


class TestNameParsing:
    def test_names_are_stripped_on_add(self, app):
        app.add_chip("   Alice   ")
        app.add_chip("\tBob\t")
        app.add_chip("  Carol  ")
        assert app.current_chips == ["Alice", "Bob", "Carol"]

    def test_empty_or_whitespace_only_input_is_ignored(self, app):
        assert app.add_chip("") is False
        assert app.add_chip("   ") is False
        assert app.add_chip("\t\n") is False
        assert app.current_chips == []

    def test_very_long_name_is_accepted(self, app):
        long_name = ("Bartholomew " * 50).strip()
        app.add_chip(long_name)
        app.add_chip("Bob")
        app.start_draw()
        assert app.assignments[0][0] == long_name
        app.update_idletasks()  # ensure rendering doesn't blow up

    def test_unicode_and_emoji_names(self, app):
        names = ["Renée", "李雷", "Søren", "🎱Champ", "O'Brien", "Müller"]
        _enter_names(app, names)
        app.start_draw()
        assert [n for n, _ in app.assignments] == names

    def test_duplicate_names_are_blocked(self, app):
        # Chip-input model dedupes case-insensitively.
        assert app.add_chip("Alice") is True
        assert app.add_chip("Alice") is False
        assert app.add_chip("alice") is False
        assert app.add_chip("ALICE") is False
        assert app.current_chips == ["Alice"]

    def test_cap_blocks_sixteenth_add(self, app):
        for i in range(15):
            assert app.add_chip(f"P{i}") is True
        assert app.add_chip("P15") is False
        assert app.add_chip("P16") is False
        assert len(app.current_chips) == 15


# ---------------------------------------------------------------------------
# Ball assignment correctness
# ---------------------------------------------------------------------------


class TestBallAssignment:
    @pytest.mark.parametrize("count", [1, 5, 10, 15])
    def test_balls_are_unique(self, app, count):
        _enter_names(app, [f"P{i}" for i in range(count)])
        app.start_draw()
        balls = [b for _, b in app.assignments]
        assert len(set(balls)) == count

    @pytest.mark.parametrize("count", [1, 5, 10, 15])
    def test_balls_are_in_valid_range(self, app, count):
        _enter_names(app, [f"P{i}" for i in range(count)])
        app.start_draw()
        for _, ball in app.assignments:
            assert 1 <= ball <= 15

    def test_full_15_uses_every_ball(self, app):
        _enter_names(app, [f"P{i}" for i in range(15)])
        app.start_draw()
        balls = sorted(b for _, b in app.assignments)
        assert balls == list(range(1, 16))

    def test_assignments_preserve_name_order(self, app):
        names = [f"Player_{i}" for i in range(10)]
        _enter_names(app, names)
        app.start_draw()
        assert [n for n, _ in app.assignments] == names

    def test_draw_is_randomized(self, app, warnings_log):
        # With 15 players and 15! permutations, repeated draws should differ.
        # start_draw() destroys the setup screen, so re-show it each iteration.
        seen = set()
        for _ in range(8):
            app.show_setup()
            _enter_names(app, [f"P{i}" for i in range(15)])
            app.start_draw()
            seen.add(tuple(b for _, b in app.assignments))
        # Extraordinarily unlikely to get identical orderings 8 times
        assert len(seen) > 1


# ---------------------------------------------------------------------------
# Reveal flow
# ---------------------------------------------------------------------------


class TestRevealFlow:
    def test_initial_reveal_state(self, app):
        _enter_names(app, ["Alice", "Bob"])
        app.start_draw()
        assert app.reveal_index == 0
        assert app.reveal_stage == "name"

    def test_name_stage_advances_to_ball_stage(self, app):
        _enter_names(app, ["Alice", "Bob"])
        app.start_draw()
        app.advance_reveal()
        assert app.reveal_index == 0
        assert app.reveal_stage == "ball"

    def test_ball_stage_advances_to_next_player(self, app):
        _enter_names(app, ["Alice", "Bob"])
        app.start_draw()
        app.advance_reveal()  # name → ball
        app.advance_reveal()  # ball → next player (name stage)
        assert app.reveal_index == 1
        assert app.reveal_stage == "name"

    def test_full_walkthrough_lands_on_summary(self, app):
        _enter_names(app, ["Alice", "Bob", "Carol"])
        app.start_draw()
        _run_full_reveal(app)
        # After last advance, reveal_index has incremented past the end
        assert app.reveal_index >= len(app.assignments)

    def test_single_player_walkthrough(self, app):
        _enter_names(app, ["Solo"])
        app.start_draw()
        app.advance_reveal()  # name → ball
        assert app.reveal_stage == "ball"
        app.advance_reveal()  # ball → summary
        assert app.reveal_index >= 1

    def test_new_game_prefills_previous_names(self, app):
        _enter_names(app, ["Alice", "Bob"])
        app.start_draw()
        _run_full_reveal(app)
        # Summary screen is now showing; clicking New Game routes to show_setup.
        # The previous lineup should be pre-populated as chips.
        app.show_setup()
        assert app.current_chips == ["Alice", "Bob"]

    def test_first_setup_screen_has_no_chips(self, app):
        # Fresh app with empty roster — tray starts empty.
        assert app.current_chips == []


# ---------------------------------------------------------------------------
# Ball rendering
# ---------------------------------------------------------------------------


class TestBallDrawing:
    @pytest.mark.parametrize("ball", list(range(1, 16)))
    def test_draw_ball_renders_each_valid_ball(self, app, ball):
        frame = tk.Frame(app)
        app._draw_ball(frame, ball)
        # A canvas child should have been created
        assert any(isinstance(c, tk.Canvas) for c in frame.winfo_children())
        frame.destroy()

    def test_draw_ball_handles_unknown_ball_gracefully(self, app):
        # Out-of-range numbers fall back to a default color, must not raise
        frame = tk.Frame(app)
        app._draw_ball(frame, 99)
        assert any(isinstance(c, tk.Canvas) for c in frame.winfo_children())
        frame.destroy()


# ---------------------------------------------------------------------------
# Summary screen
# ---------------------------------------------------------------------------


class TestSummaryScreen:
    @pytest.mark.parametrize("count", [1, 5, 15])
    def test_summary_renders_for_various_counts(self, app, count):
        _enter_names(app, [f"P{i}" for i in range(count)])
        app.start_draw()
        _run_full_reveal(app)
        app.update_idletasks()
        # show_summary was reached without raising — sanity check on state
        assert len(app.assignments) == count

    def test_summary_handles_long_names_without_raising(self, app):
        _enter_names(
            app,
            ["X" * 200, "Y" * 400, "Bartholomew the Magnificent " * 10],
        )
        app.start_draw()
        _run_full_reveal(app)
        app.update_idletasks()


# ---------------------------------------------------------------------------
# Robustness: starting a new game after one finishes
# ---------------------------------------------------------------------------


class TestRestart:
    def test_can_restart_after_completion(self, app, warnings_log):
        _enter_names(app, ["Alice", "Bob"])
        app.start_draw()
        _run_full_reveal(app)
        app.show_setup()
        _enter_names(app, ["Carol", "Dan", "Eve"])
        app.start_draw()
        assert warnings_log == []
        assert [n for n, _ in app.assignments] == ["Carol", "Dan", "Eve"]
        assert app.reveal_index == 0
        assert app.reveal_stage == "name"

    def test_back_to_back_max_size_games(self, app, warnings_log):
        for _ in range(3):
            _enter_names(app, [f"P{i}" for i in range(15)])
            app.start_draw()
            _run_full_reveal(app)
            app.show_setup()
        assert warnings_log == []


# ---------------------------------------------------------------------------
# Name-swap prank: any "M*" name (except whitelisted Marcus/Mitchell variants)
# gets prefixed with "BOZO ". display_name() preserves the original name.
# ---------------------------------------------------------------------------


class TestDisplayNameSwap:
    @pytest.mark.parametrize("name", [
        "Max", "Moey", "Mohamed", "Mohammed", "Muhammad",
        "Mary", "Mike", "Matt", "Mason", "Madison",
        "Maxamillian", "Maximilian", "Mom", "Maverick",
    ])
    def test_m_names_get_bozo_prefix(self, name):
        assert display_name(name) == f"BOZO {name}"

    @pytest.mark.parametrize("name,expected", [
        ("max", "BOZO max"),
        ("MAX", "BOZO MAX"),
        ("MoEy", "BOZO MoEy"),
        ("mOHAMED", "BOZO mOHAMED"),
    ])
    def test_m_check_is_case_insensitive(self, name, expected):
        assert display_name(name) == expected

    @pytest.mark.parametrize("name", [
        "Marcus", "marcus", "MARCUS", "Markus", "Marco", "Marcos",
        "Marc", "Mark",
        "Mitchell", "mitchell", "Mitchel", "Mitch", "MITCH",
        # Whitelist applies to the FIRST whitespace token — last name doesn't matter
        "Marcus Smith", "marcus Aurelius", "Mitchell Johnson",
        "Mitch the Bartender",
    ])
    def test_whitelisted_m_names_pass_through(self, name):
        assert display_name(name) == name

    @pytest.mark.parametrize("name", [
        "Alice", "Bob", "Carol", "Jack", "Sarah",
        "Renée", "李雷", "Søren", "O'Brien", "Champ",
        "Bartholomew", "",
        # Starts with a different letter — even if "M..." appears inside
        "Tom", "Amax", "Big Mike",
    ])
    def test_non_m_names_pass_through(self, name):
        assert display_name(name) == name

    def test_leading_whitespace_does_not_break_m_detection(self):
        assert display_name("  Max  ").startswith("BOZO ")

    def test_whitelist_is_all_lowercase(self):
        # display_name lowercases input before comparing — whitelist entries
        # must be lowercased at definition time or they silently won't match.
        for entry in kelly_ball._BOZO_M_WHITELIST:
            assert entry == entry.lower(), entry

    def test_reveal_screen_prefixes_m_name(self, app):
        _enter_names(app, ["Moey", "Alice"])
        app.start_draw()
        # Internal state keeps the real name; only the on-screen label changes.
        assert app.assignments[0][0] == "Moey"
        labels = _find_text_labels(app)
        assert "BOZO Moey" in labels

    def test_reveal_screen_keeps_non_m_names(self, app):
        _enter_names(app, ["Alice", "Moey"])
        app.start_draw()
        labels = _find_text_labels(app)
        assert "Alice" in labels
        assert not any(lbl.startswith("BOZO ") for lbl in labels)  # Moey not up yet

    def test_reveal_screen_keeps_whitelisted_m_names(self, app):
        _enter_names(app, ["Marcus", "Mitchell"])
        app.start_draw()
        labels = _find_text_labels(app)
        assert "Marcus" in labels
        assert not any(lbl.startswith("BOZO ") for lbl in labels)

    def test_summary_screen_prefixes_m_names(self, app):
        _enter_names(app, ["Alice", "Max", "Marcus", "Bob"])
        app.start_draw()
        _run_full_reveal(app)
        app.update_idletasks()
        labels = _find_text_labels(app)
        assert "Alice" in labels
        assert "Bob" in labels
        assert "BOZO Max" in labels
        assert "Marcus" in labels  # whitelisted — untouched
        assert not any(lbl == "BOZO Marcus" for lbl in labels)
        # Internal state still carries the real names
        names = [n for n, _ in app.assignments]
        assert "Max" in names
        assert "Marcus" in names

    def test_ball_assignment_unaffected_by_swap(self, app):
        _enter_names(app, ["Moey", "Max", "Mohamed", "Marcus", "Bob"])
        app.start_draw()
        balls = [b for _, b in app.assignments]
        assert len(set(balls)) == 5
        assert all(1 <= b <= 15 for b in balls)


# ---------------------------------------------------------------------------
# Rematch: previous lineup persists into the next setup screen
# ---------------------------------------------------------------------------


class TestRematchPrefill:
    def test_last_names_recorded_on_start_draw(self, app):
        _enter_names(app, ["Alice", "Bob", "Carol"])
        app.start_draw()
        assert app.last_names == ["Alice", "Bob", "Carol"]

    def test_last_names_not_set_when_no_chips(self, app):
        app.current_chips = []
        app.start_draw()
        assert app.last_names == []

    def test_prefill_survives_full_game_cycle(self, app):
        _enter_names(app, ["Alice", "Bob", "Carol"])
        app.start_draw()
        _run_full_reveal(app)
        app.show_setup()
        assert app.current_chips == ["Alice", "Bob", "Carol"]

    def test_prefill_uses_latest_game(self, app):
        _enter_names(app, ["Alice", "Bob"])
        app.start_draw()
        _run_full_reveal(app)
        app.show_setup()
        _enter_names(app, ["Carol", "Dan", "Eve"])
        app.start_draw()
        _run_full_reveal(app)
        app.show_setup()
        assert app.current_chips == ["Carol", "Dan", "Eve"]

    def test_prefill_preserves_real_names_even_when_swapped_on_screen(self, app):
        # Display swaps "Moey" → "BOZO Moey" but the stored chip stays "Moey".
        _enter_names(app, ["Moey", "Alice"])
        app.start_draw()
        _run_full_reveal(app)
        app.show_setup()
        assert app.current_chips == ["Moey", "Alice"]


# ---------------------------------------------------------------------------
# Opening splash screen with entry animation
# ---------------------------------------------------------------------------


def _find_canvases(widget) -> list:
    found = []
    for child in widget.winfo_children():
        if isinstance(child, tk.Canvas):
            found.append(child)
        found.extend(_find_canvases(child))
    return found


def _drive_splash_layout(app: KellyBallApp, attempts: int = 30) -> None:
    """Force the splash's deferred `after()` layout to run.

    The window is withdrawn during tests so it has no native geometry — we
    force a Canvas size, then pump update/sleep until `_splash_glyphs` fills.
    """
    canvas = app._splash_canvas
    if canvas is not None:
        canvas.configure(width=760, height=560)
    for _ in range(attempts):
        app.update_idletasks()
        app.update()
        if app._splash_glyphs:
            return
        time.sleep(0.05)


class TestSplashScreen:
    def test_splash_creates_canvas(self, splash_app):
        canvases = _find_canvases(splash_app.container)
        assert len(canvases) >= 1

    def test_splash_click_skips_to_setup(self, splash_app):
        # Drive deferred layout so the splash is fully initialised.
        splash_app.update()
        splash_app.update_idletasks()
        splash_app._on_splash_click()
        # Landed on setup → chip-input widgets exist.
        assert splash_app.input_entry is not None
        assert splash_app._chips_row is not None
        assert splash_app._splash_phase == "done"

    def test_splash_can_be_disabled_for_tests(self, app):
        # The `app` fixture passes show_splash_on_start=False — we land on setup.
        assert app.input_entry is not None
        assert app._chips_row is not None

    def test_app_title_uses_bozo_branding(self, splash_app):
        assert "BOZO" in splash_app.title()

    def test_splash_animation_lays_out_glyphs(self, splash_app):
        # After deferred init runs, the glyph list should have one entry per
        # visible letter / ball: B, O, Z, O, B, A, L, L = 8 (space excluded).
        _drive_splash_layout(splash_app)
        assert len(splash_app._splash_glyphs) == 8

    def test_splash_subtitle_text_is_present(self, splash_app):
        _drive_splash_layout(splash_app)
        canvas = splash_app._splash_canvas
        assert canvas is not None
        assert splash_app._splash_subtitle is not None
        text = canvas.itemcget(splash_app._splash_subtitle, "text")
        assert "click" in text.lower()


# ---------------------------------------------------------------------------
# Helpers exercised directly
# ---------------------------------------------------------------------------


class TestColorInterp:
    def test_endpoints(self):
        assert kelly_ball._interp_color("#000000", "#ffffff", 0.0) == "#000000"
        assert kelly_ball._interp_color("#000000", "#ffffff", 1.0) == "#ffffff"

    def test_midpoint_is_grey(self):
        mid = kelly_ball._interp_color("#000000", "#ffffff", 0.5)
        # 127 == 0x7f
        assert mid == "#7f7f7f"

    def test_clamps_out_of_range(self):
        assert kelly_ball._interp_color("#000000", "#ffffff", -1.0) == "#000000"
        assert kelly_ball._interp_color("#000000", "#ffffff", 2.0) == "#ffffff"


# ---------------------------------------------------------------------------
# Chip-input interactions
# ---------------------------------------------------------------------------


class TestChipInput:
    def test_add_chip_appends_in_order(self, app):
        app.add_chip("Alice")
        app.add_chip("Bob")
        app.add_chip("Carol")
        assert app.current_chips == ["Alice", "Bob", "Carol"]

    def test_remove_chip_preserves_remaining_order(self, app):
        for n in ["Alice", "Bob", "Carol", "Dan"]:
            app.add_chip(n)
        app.remove_chip("Bob")
        assert app.current_chips == ["Alice", "Carol", "Dan"]

    def test_remove_chip_is_case_insensitive(self, app):
        app.add_chip("Alice")
        assert app.remove_chip("ALICE") is True
        assert app.current_chips == []

    def test_remove_unknown_chip_is_noop(self, app):
        app.add_chip("Alice")
        assert app.remove_chip("Nobody") is False
        assert app.current_chips == ["Alice"]

    def test_count_footer_shows_table_full_at_fifteen(self, app):
        for i in range(15):
            app.add_chip(f"P{i}")
        text = app._count_label.cget("text")
        assert "15 of 15" in text
        assert "table is full" in text

    def test_chip_renders_green_regardless_of_bozo_status(self, app):
        # Chips in the tray always render green with the raw name — the
        # BOZO swap is deliberately deferred to the reveal screen so the
        # prank stays a surprise.
        for n in ("Alice", "Moey", "Max", "Marcus"):
            app.add_chip(n)
            assert app._chip_widgets[n].cget("bg") == kelly_ball.ACCENT

    def test_chip_label_shows_raw_name_not_bozo(self, app):
        app.add_chip("Max")
        chip = app._chip_widgets["Max"]
        labels = [c for c in chip.winfo_children() if isinstance(c, tk.Label)]
        texts = [lb.cget("text") for lb in labels]
        # The chip must NOT leak the BOZO swap to the player who entered it.
        assert "Max" in texts
        assert "BOZO Max" not in texts


# ---------------------------------------------------------------------------
# Recents row / roster integration
# ---------------------------------------------------------------------------


class TestRecentsAndRoster:
    def test_start_draw_writes_roster_to_disk(self, app, tmp_path):
        _enter_names(app, ["Alice", "Bob"])
        app.start_draw()
        data = json.loads((tmp_path / "roster.json").read_text())
        names = sorted(e["name"] for e in data)
        assert names == ["Alice", "Bob"]
        # Today's date should be stamped
        today = date.today().isoformat()
        for entry in data:
            assert entry["last_played"] == today
            assert entry["games"] == 1
            assert entry["enabled"] is True

    def test_start_draw_disables_players_not_in_chips(self, app, tmp_path):
        # Game 1 with Alice + Bob
        _enter_names(app, ["Alice", "Bob"])
        app.start_draw()
        _run_full_reveal(app)
        app.show_setup()
        # Game 2 with Carol only
        _enter_names(app, ["Carol"])
        app.start_draw()
        data = json.loads((tmp_path / "roster.json").read_text())
        by_name = {e["name"]: e for e in data}
        assert by_name["Carol"]["enabled"] is True
        assert by_name["Alice"]["enabled"] is False
        assert by_name["Bob"]["enabled"] is False

    def test_start_draw_increments_games_count(self, app, tmp_path):
        _enter_names(app, ["Alice"])
        app.start_draw()
        _run_full_reveal(app)
        app.show_setup()
        _enter_names(app, ["Alice"])
        app.start_draw()
        data = json.loads((tmp_path / "roster.json").read_text())
        alice = next(e for e in data if e["name"] == "Alice")
        assert alice["games"] == 2

    def test_roster_prepopulates_chip_tray_on_next_launch(self, app, tmp_path):
        # First game establishes the enabled roster
        _enter_names(app, ["Alice", "Bob"])
        app.start_draw()
        # Now simulate a fresh launch by constructing a new app with the same
        # roster path. last_names is empty so the seed comes from the roster.
        app.destroy()
        fresh = KellyBallApp(
            show_splash_on_start=False,
            roster_path=tmp_path / "roster.json",
        )
        fresh.withdraw()
        try:
            assert sorted(fresh.current_chips) == ["Alice", "Bob"]
        finally:
            fresh.destroy()

    def test_forget_roster_entry_removes_and_persists(self, app, tmp_path):
        _enter_names(app, ["Alice", "Bob"])
        app.start_draw()
        _run_full_reveal(app)
        app.show_setup()
        # Remove Bob from chips first so the recents row shows him
        app.remove_chip("Bob")
        app._forget_roster_entry("Bob")
        names = [e["name"] for e in app.roster]
        assert "Bob" not in names
        data = json.loads((tmp_path / "roster.json").read_text())
        assert all(e["name"] != "Bob" for e in data)


# ---------------------------------------------------------------------------
# load_roster / save_roster — exercised directly without the GUI
# ---------------------------------------------------------------------------


class TestRosterIO:
    def test_missing_file_returns_empty(self, tmp_path):
        assert load_roster(tmp_path / "nope.json") == []

    def test_malformed_file_returns_empty(self, tmp_path):
        p = tmp_path / "roster.json"
        p.write_text("{ not valid json")
        assert load_roster(p) == []

    def test_top_level_not_list_returns_empty(self, tmp_path):
        p = tmp_path / "roster.json"
        p.write_text('{"name": "Alice"}')
        assert load_roster(p) == []

    def test_save_then_load_roundtrip(self, tmp_path):
        p = tmp_path / "roster.json"
        roster = [
            {"name": "Alice", "last_played": "2026-05-28",
             "games": 3, "wins": 2, "enabled": True},
            {"name": "Bob", "last_played": "2026-05-20",
             "games": 1, "wins": 0, "enabled": False},
        ]
        save_roster(p, roster)
        loaded = load_roster(p)
        assert sorted(loaded, key=lambda e: e["name"]) == sorted(
            roster, key=lambda e: e["name"]
        )

    def test_load_fills_missing_wins_with_zero(self, tmp_path):
        # Backwards-compat: a roster written before `wins` existed.
        p = tmp_path / "roster.json"
        p.write_text(json.dumps([
            {"name": "Alice", "last_played": "2026-05-28",
             "games": 3, "enabled": True},
        ]))
        loaded = load_roster(p)
        assert loaded[0]["wins"] == 0

    def test_dedupe_keeps_most_recent_played(self, tmp_path):
        p = tmp_path / "roster.json"
        p.write_text(json.dumps([
            {"name": "Alice", "last_played": "2026-01-01",
             "games": 1, "enabled": False},
            {"name": "alice", "last_played": "2026-05-01",
             "games": 7, "enabled": True},
        ]))
        loaded = load_roster(p)
        assert len(loaded) == 1
        # Most recent wins on the dedupe
        assert loaded[0]["last_played"] == "2026-05-01"
        assert loaded[0]["games"] == 7

    def test_invalid_entries_are_skipped(self, tmp_path):
        p = tmp_path / "roster.json"
        p.write_text(json.dumps([
            {"name": "Alice", "last_played": "2026-05-01", "games": 1,
             "enabled": True},
            "not a dict",
            {"no_name_field": True},
            {"name": "", "last_played": "2026-05-01"},
            {"name": "   ", "last_played": "2026-05-01"},
            {"name": "Bob", "last_played": "2026-05-02", "games": 2,
             "enabled": False},
        ]))
        loaded = load_roster(p)
        names = sorted(e["name"] for e in loaded)
        assert names == ["Alice", "Bob"]

    def test_save_is_atomic(self, tmp_path):
        # The .tmp sidecar should not linger after a successful save.
        p = tmp_path / "roster.json"
        save_roster(p, [{"name": "Alice", "last_played": "2026-05-28",
                         "games": 1, "enabled": True}])
        assert p.exists()
        assert not (tmp_path / "roster.json.tmp").exists()

    def test_default_roster_path_under_home(self):
        path = kelly_ball.default_roster_path()
        assert path.name == "roster.json"
        assert path.parent.name == ".bozo_ball"


# ---------------------------------------------------------------------------
# Winner tracking
# ---------------------------------------------------------------------------


class TestWinnerTracking:
    def test_record_winner_increments_wins(self, app, tmp_path):
        _enter_names(app, ["Alice", "Bob"])
        app.start_draw()
        app._record_winner("Alice")
        alice = next(e for e in app.roster if e["name"] == "Alice")
        assert alice["wins"] == 1
        # Marked as winner for this game
        assert "Alice" in app.current_winners

    def test_record_winner_persists(self, app, tmp_path):
        _enter_names(app, ["Alice"])
        app.start_draw()
        app._record_winner("Alice")
        data = json.loads((tmp_path / "roster.json").read_text())
        alice = next(e for e in data if e["name"] == "Alice")
        assert alice["wins"] == 1

    def test_start_draw_resets_current_winners(self, app):
        _enter_names(app, ["Alice", "Bob"])
        app.start_draw()
        app._record_winner("Alice")
        assert "Alice" in app.current_winners
        _run_full_reveal(app)
        app.show_setup()
        _enter_names(app, ["Carol"])
        app.start_draw()
        assert app.current_winners == set()


# ---------------------------------------------------------------------------
# Tournament mode
# ---------------------------------------------------------------------------


class TestTournamentMode:
    def test_starting_a_tournament_sets_round_one(self, app):
        app.tournament_mode = True
        _enter_names(app, ["Alice", "Bob", "Carol", "Dan"])
        app.start_draw()
        assert app.tournament_round == 1

    def test_next_round_keeps_only_winners(self, app):
        app.tournament_mode = True
        _enter_names(app, ["Alice", "Bob", "Carol", "Dan"])
        app.start_draw()
        app._next_tournament_round(["Alice", "Carol"])
        assert app.tournament_round == 2
        assert [n for n, _ in app.assignments] == ["Alice", "Carol"]
        # Wins recorded for advancers — set fresh each round
        assert app.current_winners == set()

    def test_next_round_redraws_balls(self, app):
        app.tournament_mode = True
        _enter_names(app, [f"P{i}" for i in range(8)])
        app.start_draw()
        original = [b for _, b in app.assignments]
        winners = [n for n, _ in app.assignments[:4]]
        app._next_tournament_round(winners)
        new = [b for _, b in app.assignments]
        # Different player set → different ball list
        assert len(new) == 4
        # Balls must still be unique within the new round
        assert len(set(new)) == 4

    def test_single_player_left_shows_champion(self, app):
        app.tournament_mode = True
        _enter_names(app, ["Alice", "Bob", "Carol"])
        app.start_draw()
        # Going from 3 → 1 directly should land on the champion screen.
        app._next_tournament_round(["Alice"])
        # Champion screen has no "assignments" rebuilt; verify by walking labels
        labels = _find_text_labels(app)
        assert "CHAMPION" in labels
        # And the winner's name (or display name) appears
        assert any("Alice" in lbl for lbl in labels)

    def test_zero_winners_advances_to_champion_with_none(self, app):
        app.tournament_mode = True
        _enter_names(app, ["Alice", "Bob"])
        app.start_draw()
        app._next_tournament_round([])
        labels = _find_text_labels(app)
        assert "CHAMPION" in labels

    def test_non_tournament_mode_default(self, app):
        # Default state — must not be in tournament mode
        assert app.tournament_mode is False
        assert app.tournament_round == 0


# ---------------------------------------------------------------------------
# Settings persistence + behavior
# ---------------------------------------------------------------------------


class TestSettings:
    def test_default_settings_when_file_missing(self, tmp_path):
        s = kelly_ball.load_settings(tmp_path / "settings.json")
        assert s["bozo_enabled"] is True
        assert isinstance(s["whitelist"], list)
        assert "marcus" in s["whitelist"]

    def test_settings_roundtrip(self, tmp_path):
        p = tmp_path / "settings.json"
        custom = {"bozo_enabled": False, "whitelist": ["marcus", "mitchell"]}
        kelly_ball.save_settings(p, custom)
        loaded = kelly_ball.load_settings(p)
        assert loaded["bozo_enabled"] is False
        assert loaded["whitelist"] == ["marcus", "mitchell"]

    def test_malformed_settings_falls_back(self, tmp_path):
        p = tmp_path / "settings.json"
        p.write_text("{ not json")
        s = kelly_ball.load_settings(p)
        assert s["bozo_enabled"] is True

    def test_app_uses_loaded_settings_for_display_name(self, app, tmp_path):
        # Disable BOZO via settings and confirm the chip label shows raw name.
        app.settings["bozo_enabled"] = False
        kelly_ball.save_settings(app.settings_path, app.settings)
        app.show_setup()
        app.add_chip("Moey")
        chip = app._chip_widgets["Moey"]
        labels = [c for c in chip.winfo_children() if isinstance(c, tk.Label)]
        assert any(lb.cget("text") == "Moey" for lb in labels)

    def test_custom_whitelist_keeps_listed_names(self, app):
        # Add "Mike" to the whitelist → Mike no longer gets bozoified.
        app.settings["whitelist"] = list(
            kelly_ball.DEFAULT_BOZO_M_WHITELIST
        ) + ["mike"]
        assert app._dn("Mike") == "Mike"
        # Other M names still get swapped
        assert app._dn("Max") == "BOZO Max"

    def test_display_name_module_function_accepts_whitelist_kwarg(self):
        custom = frozenset(["max"])
        # Max is now whitelisted; Marcus is no longer.
        assert display_name("Max", whitelist=custom) == "Max"
        assert display_name("Marcus", whitelist=custom) == "BOZO Marcus"

    def test_display_name_disabled_returns_input_unchanged(self):
        assert display_name("Moey", enabled=False) == "Moey"
        assert display_name("Max", enabled=False) == "Max"


# ---------------------------------------------------------------------------
# Intro flash before the splash screen
# ---------------------------------------------------------------------------


class TestIntroFlash:
    def test_find_intro_image_returns_none_when_absent(self, tmp_path, monkeypatch):
        # Point both resource search locations at empty tmp dirs; no intro file exists.
        monkeypatch.setattr(kelly_ball, "_resource_dir", lambda: tmp_path)
        monkeypatch.setattr(
            kelly_ball, "EXTERNAL_RESOURCE_DIR", tmp_path / "nonexistent"
        )
        assert kelly_ball.find_intro_image() is None

    def test_find_intro_image_returns_png_when_present(self, tmp_path, monkeypatch):
        # 1x1 transparent PNG (minimum valid file) — Tk should accept it.
        png_bytes = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
            "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae"
            "426082"
        )
        (tmp_path / "intro.png").write_bytes(png_bytes)
        monkeypatch.setattr(kelly_ball, "_resource_dir", lambda: tmp_path)
        found = kelly_ball.find_intro_image()
        assert found is not None
        assert found.name == "intro.png"

    def test_bozo_flash_arms_on_ball_stage_for_bozoified_player(self, app):
        # Set up a player whose name gets bozoified (M-prefixed, not whitelisted).
        _enter_names(app, ["Max", "Alice"])
        app.start_draw()
        # First player (Max) — advance from name → ball stage.
        app.advance_reveal()
        # The flash should render on the first call; the flag flips true.
        assert app._bozo_flash_done is True

    def test_bozo_flash_does_not_fire_for_normal_player(self, app):
        _enter_names(app, ["Alice", "Bob"])
        app.start_draw()
        app.advance_reveal()  # name → ball for Alice (not bozoified)
        # Flash flag stays False because Alice doesn't trigger it.
        assert app._bozo_flash_done is False

    def test_bozo_flash_resets_between_players(self, app):
        _enter_names(app, ["Max", "Mohamed"])
        app.start_draw()
        # Player 1 (Max): advance to ball — flash arms
        app.advance_reveal()
        assert app._bozo_flash_done is True
        # Simulate the flash completing
        app._bozo_flash_done = True
        # Advance past the ball stage to next player
        app.advance_reveal()  # ball → next player name stage
        # Flag should have been reset for the next player
        assert app._bozo_flash_done is False
