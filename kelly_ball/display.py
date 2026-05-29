"""Name transformation (the BOZO prank) and color interpolation."""
from .theme import DEFAULT_BOZO_M_WHITELIST


_BOZO_M_WHITELIST = frozenset(s.lower() for s in DEFAULT_BOZO_M_WHITELIST)


def display_name(name: str, *, enabled: bool = True, whitelist=None) -> str:
    if not enabled:
        return name
    wl = whitelist if whitelist is not None else _BOZO_M_WHITELIST
    stripped = name.strip()
    if not stripped or not stripped[0].lower() == "m":
        return name
    first_word = stripped.split()[0].lower()
    if first_word in wl:
        return name
    return f"BOZO {name}"


def _interp_color(c1: str, c2: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"
