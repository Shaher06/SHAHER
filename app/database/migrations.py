"""Schema migrations. The schema version lives in SQLite's PRAGMA user_version.

Rules: never edit an old migration after release - add a new one. Migrations only
ever ADD things, so opening the app never destroys existing user data.
"""
import logging
import sqlite3

log = logging.getLogger("shaher.db")

MIGRATION_1 = """
CREATE TABLE commitments (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT    NOT NULL CHECK (length(trim(title)) > 0),
    description      TEXT    NOT NULL DEFAULT '',
    due_at           TEXT    NOT NULL,
    priority         TEXT    NOT NULL DEFAULT 'medium' CHECK (priority IN ('low','medium','high')),
    category         TEXT    NOT NULL DEFAULT '',
    status           TEXT    NOT NULL DEFAULT 'open'   CHECK (status IN ('open','completed','archived')),
    reminder_enabled INTEGER NOT NULL DEFAULT 0 CHECK (reminder_enabled IN (0,1)),
    reminder_at      TEXT,
    created_at       TEXT    NOT NULL,
    updated_at       TEXT    NOT NULL,
    completed_at     TEXT,
    archived_at      TEXT
);
CREATE INDEX idx_commitments_status_due ON commitments(status, due_at);
CREATE INDEX idx_commitments_category   ON commitments(category);

CREATE TABLE habits (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT    NOT NULL CHECK (length(trim(name)) > 0),
    start_date       TEXT    NOT NULL,
    target_days      INTEGER NOT NULL DEFAULT 15 CHECK (target_days > 0),
    reminder_enabled INTEGER NOT NULL DEFAULT 0 CHECK (reminder_enabled IN (0,1)),
    reminder_time    TEXT,
    status           TEXT    NOT NULL DEFAULT 'active' CHECK (status IN ('active','archived')),
    created_at       TEXT    NOT NULL,
    archived_at      TEXT
);

CREATE TABLE habit_records (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id    INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    record_date TEXT    NOT NULL,
    result      TEXT    NOT NULL CHECK (result IN ('success','setback')),
    note        TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL,
    UNIQUE (habit_id, record_date)
);
CREATE INDEX idx_habit_records_habit ON habit_records(habit_id, record_date);

CREATE TABLE settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

# Column meanings:
#   commitments.reminder_sent_at - when the in-app (Windows fallback) reminder last fired
#   *.is_demo                    - rows created by the optional demo-data action
MIGRATION_2 = """
ALTER TABLE commitments ADD COLUMN reminder_sent_at TEXT;
ALTER TABLE commitments ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0;
ALTER TABLE habits      ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0;
"""

# commitments.focus_date - the day (YYYY-MM-DD) the user picked this item as a Daily Focus priority
MIGRATION_3 = """
ALTER TABLE commitments ADD COLUMN focus_date TEXT;
CREATE INDEX idx_commitments_focus ON commitments(focus_date)
"""

MIGRATIONS = [(1, MIGRATION_1), (2, MIGRATION_2), (3, MIGRATION_3)]
LATEST_VERSION = MIGRATIONS[-1][0]


def get_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def migrate(conn: sqlite3.Connection, target: int = LATEST_VERSION) -> int:
    """Apply every pending migration up to `target`. Each one is atomic."""
    current = get_version(conn)
    if current > LATEST_VERSION:
        raise RuntimeError(
            f"قاعدة البيانات أحدث من هذا الإصدار من التطبيق (النسخة {current}). حدّث التطبيق."
        )
    for version, script in MIGRATIONS:
        if version <= current or version > target:
            continue
        log.info("Applying migration %s", version)
        try:
            conn.execute("BEGIN")
            for statement in script.split(";"):
                if statement.strip():
                    conn.execute(statement)
            conn.execute(f"PRAGMA user_version = {int(version)}")
            conn.execute("COMMIT")
        except sqlite3.Error:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            log.exception("Migration %s failed and was rolled back", version)
            raise
    return get_version(conn)
