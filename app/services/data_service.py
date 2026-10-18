"""Backup validation + restore, CSV/JSON export, and explicit data deletion."""
import csv
import json
import logging
import shutil
import sqlite3
from pathlib import Path
from typing import List

from app import config
from app.database.db import transaction
from app.database.migrations import LATEST_VERSION, migrate
from app.services import backup_service
from app.utils import dates
from app.utils.validation import ValidationError

log = logging.getLogger("shaher.data")
REQUIRED_TABLES = {"commitments", "habits", "habit_records", "settings"}
COMMITMENT_COLUMNS = ["id", "title", "description", "due_at", "priority", "category", "status",
                      "reminder_enabled", "reminder_at", "created_at", "completed_at", "archived_at"]


def exports_dir() -> Path:
    path = config.data_dir() / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _stamp() -> str:
    return dates.now().strftime("%Y%m%d_%H%M%S")


def export_csv(conn: sqlite3.Connection, dest_dir=None) -> Path:
    """Commitments as UTF-8 CSV (with BOM so Excel shows Arabic correctly)."""
    target = Path(dest_dir or exports_dir()) / f"shaher_commitments_{_stamp()}.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = conn.execute(f"SELECT {', '.join(COMMITMENT_COLUMNS)} FROM commitments ORDER BY due_at")
    with open(target, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(COMMITMENT_COLUMNS)
        writer.writerows(tuple(r) for r in rows)
    return target


def export_json(conn: sqlite3.Connection, dest_dir=None) -> Path:
    """Commitments, habits and habit records as one JSON file (no preferences)."""
    target = Path(dest_dir or exports_dir()) / f"shaher_export_{_stamp()}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    def table(sql):
        return [dict(r) for r in conn.execute(sql)]
    payload = {
        "app": "SHAHER", "exported_at": dates.to_ts(dates.now()), "schema_version": LATEST_VERSION,
        "commitments": table("SELECT * FROM commitments ORDER BY id"),
        "habits": table("SELECT * FROM habits ORDER BY id"),
        "habit_records": table("SELECT * FROM habit_records ORDER BY habit_id, record_date"),
    }
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return target


def validate_backup(path) -> None:
    """Raises ValidationError unless `path` is an intact SHAHER database this app can read."""
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValidationError("err.backup_invalid")
    try:
        probe = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        raise ValidationError("err.backup_invalid")
    try:
        if probe.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValidationError("err.backup_invalid")
        tables = {r[0] for r in probe.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        version = probe.execute("PRAGMA user_version").fetchone()[0]
    except sqlite3.DatabaseError:
        raise ValidationError("err.backup_invalid")
    finally:
        probe.close()
    if not REQUIRED_TABLES <= tables or version < 1:
        raise ValidationError("err.backup_invalid")
    if version > LATEST_VERSION:
        raise ValidationError("err.backup_newer")


def restore_backup(conn: sqlite3.Connection, path, reminders=None) -> Path:
    """Replace the live data with a validated backup. The current data is saved first
    (pre_restore_*.db) so a restore can itself be undone. Returns that safety copy."""
    validate_backup(path)
    safety = backup_service.export_backup(conn)
    safety = safety.rename(safety.with_name(safety.name.replace("shaher_backup_", "pre_restore_")))
    src = sqlite3.connect(str(path))
    try:
        src.backup(conn)                 # copies pages into the live connection
    finally:
        src.close()
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)                        # an older backup is upgraded in place
    if reminders is not None:
        reminders.resync_all()
    log.info("restore finished")
    return safety


def delete_all_data(conn: sqlite3.Connection, reminders=None) -> None:
    """Delete every commitment, habit and record. Preferences are kept. UI must confirm first."""
    ids = [r[0] for r in conn.execute("SELECT id FROM commitments")]
    hids = [r[0] for r in conn.execute("SELECT id FROM habits")]
    with transaction(conn):
        conn.execute("DELETE FROM commitments")
        conn.execute("DELETE FROM habits")            # records cascade
    if reminders is not None:
        for i in ids:
            reminders.cancel_commitment(i)
        for i in hids:
            reminders.backend.cancel(f"h{i}")
