import sqlite3
from pathlib import Path
from typing import List

from app import config
from app.utils import dates


def export_backup(conn: sqlite3.Connection, dest_dir=None) -> Path:
    """Copy the live database to a timestamped file using SQLite's safe backup API."""
    dest = Path(dest_dir) if dest_dir else config.backups_dir()
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / f"shaher_backup_{dates.now().strftime('%Y%m%d_%H%M%S')}.db"
    out = sqlite3.connect(str(target))
    try:
        conn.backup(out)
    finally:
        out.close()
    return target


def list_backups(dest_dir=None) -> List[Path]:
    dest = Path(dest_dir) if dest_dir else config.backups_dir()
    return sorted(dest.glob("shaher_backup_*.db"), reverse=True)
