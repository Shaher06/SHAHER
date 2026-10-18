import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app import config
from app.database.migrations import migrate


def connect(path=None) -> sqlite3.Connection:
    """Open (and create/upgrade if needed) the SQLite database.

    `path` may be ':memory:' or a file path. Existing data is never deleted.
    """
    path = str(path) if path is not None else str(config.db_path())
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None)  # we manage transactions ourselves
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection):
    """All-or-nothing group of changes:  with transaction(conn): ..."""
    conn.execute("BEGIN")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
