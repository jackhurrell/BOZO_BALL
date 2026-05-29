"""Roster + settings load/save (JSON, atomic, validated)."""
import json
import os
from pathlib import Path

from .theme import (
    DEFAULT_SETTINGS,
    ROSTER_DIR_NAME,
    ROSTER_FILENAME,
    SETTINGS_FILENAME,
)


def default_roster_path() -> Path:
    return Path.home() / ROSTER_DIR_NAME / ROSTER_FILENAME


def default_settings_path() -> Path:
    return Path.home() / ROSTER_DIR_NAME / SETTINGS_FILENAME


def load_settings(path: Path) -> dict:
    base = {
        "bozo_enabled": DEFAULT_SETTINGS["bozo_enabled"],
        "whitelist": list(DEFAULT_SETTINGS["whitelist"]),
        "background_music_enabled": DEFAULT_SETTINGS["background_music_enabled"],
        "bozo_surprise_mode": DEFAULT_SETTINGS["bozo_surprise_mode"],
    }
    try:
        if not path.exists():
            return base
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return base
    if not isinstance(raw, dict):
        return base
    if isinstance(raw.get("bozo_enabled"), bool):
        base["bozo_enabled"] = raw["bozo_enabled"]
    if isinstance(raw.get("background_music_enabled"), bool):
        base["background_music_enabled"] = raw["background_music_enabled"]
    if isinstance(raw.get("bozo_surprise_mode"), bool):
        base["bozo_surprise_mode"] = raw["bozo_surprise_mode"]
    wl = raw.get("whitelist")
    if isinstance(wl, list):
        base["whitelist"] = [s for s in wl if isinstance(s, str) and s.strip()]
    return base


def save_settings(path: Path, settings: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except OSError:
        pass


def load_roster(path: Path) -> list[dict]:
    try:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list):
        return []

    seen: dict[str, dict] = {}
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        key = name.strip().lower()
        normalized = {
            "name": name,
            "last_played": str(entry.get("last_played", "") or ""),
            "games": int(entry.get("games", 0) or 0),
            "wins": int(entry.get("wins", 0) or 0),
            "enabled": bool(entry.get("enabled", False)),
        }
        existing = seen.get(key)
        if existing is None or normalized["last_played"] > existing["last_played"]:
            seen[key] = normalized
    return list(seen.values())


def save_roster(path: Path, roster: list[dict]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(roster, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except OSError:
        pass  # best-effort persistence
