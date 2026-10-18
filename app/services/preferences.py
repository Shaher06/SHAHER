"""Typed, validated user preferences stored in the `settings` table."""
import logging
from typing import Any, Dict

from app.services.settings_service import SettingsService

log = logging.getLogger("shaher.prefs")

# name -> (default, allowed values or None for free-form)
SPEC: Dict[str, tuple] = {
    "language": ("ar", ("ar", "en")),
    "theme_mode": ("light", ("light", "dark", "system")),
    "accent": ("teal", ("teal", "ocean", "emerald", "violet", "rose", "amber", "graphite", "custom")),
    "custom_accent": ("", None),                       # '#RRGGBB'
    "density": ("comfortable", ("comfortable", "compact")),
    "text_scale": ("standard", ("standard", "large")),
    "radius": ("soft", ("sharp", "soft", "round")),
    "decor": ("1", ("0", "1")),                        # subtle gradient background
    "reduced_motion": ("0", ("0", "1")),
    "haptics": ("1", ("0", "1")),
    "digits": ("western", ("western", "arabic")),
    "user_name": ("", None),
    "onboarded": ("0", ("0", "1")),
    "encouragement": ("normal", ("off", "gentle", "normal")),
    "quiet_mode": ("0", ("0", "1")),
    "reminder_offset_minutes": ("30", ("0", "10", "30", "60", "1440")),
    "reminder_default_on": ("0", ("0", "1")),
    "default_priority": ("medium", ("low", "medium", "high")),
    "sort": ("urgency", ("urgency", "date", "priority")),
    "last_open_date": ("", None),
    "enc_last_ts": ("", None),
    "enc_last_key": ("", None),
    "enc_completed_count": ("0", None),
}
MAX_NAME = 30


class Preferences:
    def __init__(self, settings: SettingsService):
        self.s = settings

    def get(self, name: str) -> str:
        default, allowed = SPEC[name]
        value = self.s.get(name, default)
        if allowed is not None and value not in allowed:
            log.warning("invalid stored value for %s, using default", name)
            return default
        return value

    def set(self, name: str, value: Any) -> None:
        default, allowed = SPEC[name]
        value = str(value).strip()
        if name == "user_name":
            value = " ".join(value.split())[:MAX_NAME]
        if name == "custom_accent" and value and not _valid_hex(value):
            raise ValueError("bad colour")
        if allowed is not None and value not in allowed:
            raise ValueError(f"{value!r} is not allowed for {name}")
        self.s.set(name, value)

    def flag(self, name: str) -> bool:
        return self.get(name) == "1"

    def set_flag(self, name: str, on: bool) -> None:
        self.set(name, "1" if on else "0")

    def int(self, name: str, fallback: int = 0) -> int:
        try:
            return int(self.s.get(name, SPEC[name][0]))
        except (TypeError, ValueError):
            return fallback

    @property
    def needs_onboarding(self) -> bool:
        return not self.flag("onboarded")

    def reset_preferences(self) -> None:
        """Back to defaults. Commitments, habits and records are NOT touched.
        The name and the 'onboarded' flag are kept so the user is not asked again."""
        keep = {"user_name", "onboarded"}
        for name in SPEC:
            if name not in keep:
                self.s.conn.execute("DELETE FROM settings WHERE key=?", (name,))


def _valid_hex(value: str) -> bool:
    return len(value) == 7 and value[0] == "#" and all(c in "0123456789abcdefABCDEF" for c in value[1:])
