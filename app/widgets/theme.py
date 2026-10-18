"""Design system: colours, sizes and fonts. Call apply() whenever a preference changes, then
rebuild the screens (widgets read these module attributes when they are created).

Light = warm ivory "glass" cards. Dark = deep navy equivalent (not an inversion).
All text/accent pairs are contrast-checked in tests/test_theme.py.
"""
from kivy.core.text import LabelBase
from kivy.metrics import dp as _dp, sp as _sp
from kivy.utils import get_color_from_hex as _hx


def hx(value):
    """Hex string -> RGBA tuple (always a tuple, so colours can be concatenated safely)."""
    return tuple(_hx(value))

from app import config

FONT = str(config.font_path())
FONT_BOLD = str(config.font_bold_path())

PALETTES = {
    "light": dict(bg="#F7F2E8", bg2="#EDE6D6", surface=(1, 1, 1, 0.74), surface_solid="#FFFFFF",
                  field="#FFFFFF", border="#E4DCCB", text="#1B2A29", muted="#5B6968",
                  danger="#B3261E", warning="#8F5A00", shadow=(0.25, 0.2, 0.1, 0.07)),
    "dark": dict(bg="#0C1620", bg2="#101D2B", surface=(0.13, 0.2, 0.28, 0.78), surface_solid="#16222F",
                 field="#1C2C3E", border="#2B3C50", text="#E9EFF5", muted="#9AABBD",
                 danger="#FF8A80", warning="#FFC247", shadow=(0, 0, 0, 0.25)),
}
ACCENTS = {   # name: (for light mode, for dark mode)
    "teal": ("#0F8F82", "#3CD0C2"), "ocean": ("#2563C9", "#6AA8FF"),
    "emerald": ("#1B8A4F", "#46D391"), "violet": ("#6B4BD6", "#A58BFF"),
    "rose": ("#C73A6E", "#FF7AA6"), "amber": ("#B86E00", "#FFB02E"),
    "graphite": ("#46515C", "#B4C0CC"),
}
RADII = {"sharp": 6, "soft": 14, "round": 24}


# ---------- colour maths (WCAG contrast) ----------
def _lin(c):
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = (_lin(x) for x in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def ensure_contrast(color, background, minimum):
    """Nudge `color` toward black/white until it reaches `minimum`:1 against `background`."""
    color = tuple(color[:3])
    target = (0, 0, 0) if luminance(background) > 0.4 else (1, 1, 1)
    for step in range(21):
        mix = tuple(c + (t - c) * step / 20 for c, t in zip(color, target))
        if contrast(mix, background) >= minimum:
            return mix + (1,)
    return target + (1,)


def on_color(bg):
    dark, light = (0.07, 0.12, 0.11), (1, 1, 1)
    return dark + (1,) if contrast(dark, bg) >= contrast(light, bg) else light + (1,)


# ---------- current theme (module attributes; reassigned by apply) ----------
MODE = "light"
DENSITY = 1.0
TEXT_SCALE = 1.0
RADIUS = _dp(14)
DECOR = True
BG = BG2 = SURFACE = SURFACE_SOLID = FIELD = BORDER = TEXT = MUTED = SHADOW = (0, 0, 0, 1)
ACCENT = ACCENT_TEXT = ACCENT_SOFT = ON_ACCENT = DANGER = WARNING = (0, 0, 0, 1)
PRIORITY_COLORS = {}


def apply(mode="light", accent="teal", custom="", density="comfortable", text_scale="standard",
          radius="soft", decor=True, system_mode="light"):
    global MODE, DENSITY, TEXT_SCALE, RADIUS, DECOR, BG, BG2, SURFACE, SURFACE_SOLID, FIELD, BORDER
    global TEXT, MUTED, SHADOW, ACCENT, ACCENT_TEXT, ACCENT_SOFT, ON_ACCENT, DANGER, WARNING, PRIORITY_COLORS
    MODE = system_mode if mode == "system" else mode
    p = PALETTES[MODE]
    BG, BG2 = hx(p["bg"]), hx(p["bg2"])
    SURFACE, SURFACE_SOLID, FIELD = p["surface"], hx(p["surface_solid"]), hx(p["field"])
    BORDER, TEXT, MUTED, SHADOW = hx(p["border"]), hx(p["text"]), hx(p["muted"]), p["shadow"]
    DANGER, WARNING = hx(p["danger"]), hx(p["warning"])
    if accent == "custom" and custom:
        base = hx(custom)
    else:
        light_hex, dark_hex = ACCENTS.get(accent, ACCENTS["teal"])
        base = hx(dark_hex if MODE == "dark" else light_hex)
    # Fill colour: light theme -> dark enough for WHITE text (4.5:1); dark theme -> light enough for dark text.
    if MODE == "light":
        ACCENT = ensure_contrast(base, (1, 1, 1), 4.5)
    else:
        ACCENT = ensure_contrast(base, (0.07, 0.12, 0.11), 4.5)
    ACCENT_TEXT = ensure_contrast(base, SURFACE_SOLID, 4.5)  # accent used as small text
    ACCENT_SOFT = ACCENT[:3] + (0.16,)
    ON_ACCENT = on_color(ACCENT)
    if contrast(ON_ACCENT, ACCENT) < 4.5:      # last resort: push the fill until text is readable
        ACCENT = ensure_contrast(ACCENT, ON_ACCENT, 4.5)
    DENSITY = 0.86 if density == "compact" else 1.0
    TEXT_SCALE = 1.2 if text_scale == "large" else 1.0
    RADIUS = _dp(RADII.get(radius, 14))
    DECOR = bool(decor)
    PRIORITY_COLORS = {"low": MUTED, "medium": ACCENT_TEXT, "high": WARNING}


def dp(n):
    return _dp(n)


def gap(n):
    """Spacing that follows the density preference."""
    return _dp(n) * DENSITY


def fs(n):
    """Font size that follows the text-size preference."""
    return _sp(n) * TEXT_SCALE


def register_fonts() -> None:
    """Make the bundled Arabic-capable font the default for every Kivy widget."""
    LabelBase.register(name="Roboto", fn_regular=FONT, fn_bold=FONT_BOLD)
    LabelBase.register(name="Shaher", fn_regular=FONT, fn_bold=FONT_BOLD)


apply()
