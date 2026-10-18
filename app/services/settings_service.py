import logging
import sqlite3

log = logging.getLogger("shaher.settings")

DEFAULTS = {
    "reminder_offset_minutes": "30",   # default reminder: this long before the due time
}


class SettingsService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get(self, key: str, default=None) -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        if row is None:
            return DEFAULTS.get(key, default)
        return row["value"]

    def get_int(self, key: str, default: int) -> int:
        """Missing or malformed values fall back to the default instead of crashing."""
        try:
            return int(self.get(key, default))
        except (TypeError, ValueError):
            log.warning("malformed setting %s, using default", key)
            return default

    def set(self, key: str, value) -> None:
        self.conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
