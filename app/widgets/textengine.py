"""Chooses the Arabic rendering mode at start-up.

Default and only VERIFIED mode: "reshape" (arabic-reshaper + python-bidi, see app/utils/arabic.py).
It was checked against a real shaping renderer (tests/test_arabic_visual.py).

A probe also measures whether the platform text renderer joins Arabic letters by itself (four
joined letters are narrower than four isolated ones). The result is only LOGGED and shown in
Settings > About for troubleshooting. We deliberately do not switch modes automatically: how a
shaping renderer treats already-shaped text is unverified, and wrong text is worse than a
different mode. Force a mode with the environment variable SHAHER_TEXT_MODE=reshape|native.
"""
import logging
import os

from kivy.core.text import Label as CoreLabel

from app.utils import arabic
from app.widgets import theme

log = logging.getLogger("shaher.text")
_detected = None


def probe_native_shaping() -> bool:
    def rendered_width(text):          # measure the REAL texture: get_extents() ignores shaping
        label = CoreLabel(text=text, font_name=theme.FONT, font_size=40)
        label.refresh()
        return label.texture.width
    one, four = rendered_width("ب"), rendered_width("بببب")
    log.info("shaping probe: isolated=%s joined4=%s", one, four)
    return four < 3.6 * one            # shaped (joined) forms are narrower; isolated forms are exactly 4x


def configure() -> str:
    """Set the mode in app.utils.arabic and return it."""
    global _detected
    forced = os.environ.get("SHAHER_TEXT_MODE", "").lower()
    mode = forced if forced in ("native", "reshape") else "reshape"
    try:
        shapes = probe_native_shaping()
        log.info("renderer joins Arabic letters natively: %s (informational; mode stays %s)", shapes, mode)
    except Exception:
        log.exception("shaping probe failed (ignored)")
    arabic.set_mode(mode)
    _detected = mode
    log.info("Arabic text mode: %s", mode)
    return mode


def mode() -> str:
    return _detected or arabic.get_mode()
