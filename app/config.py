"""Where SHAHER keeps its files. No Kivy imports here, so tests can use it."""
import os
import sys
from pathlib import Path

APP_NAME = "SHAHER"
DB_FILENAME = "shaher.db"


def is_android() -> bool:
    return "ANDROID_ARGUMENT" in os.environ or "ANDROID_PRIVATE" in os.environ


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    """Writable folder for the database, logs and backups.

    Order of preference:
    1. SHAHER_DATA_DIR environment variable (used by tests and for dev copies)
    2. Android: the app's private files directory
    3. Windows: %APPDATA%\\SHAHER
    4. Other systems: ~/.local/share/shaher
    """
    override = os.environ.get("SHAHER_DATA_DIR")
    if override:
        path = Path(override)
    elif is_android():
        path = Path(os.environ.get("ANDROID_PRIVATE") or os.environ["ANDROID_ARGUMENT"]) / "shaher_data"
    elif sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or str(Path.home())
        path = Path(base) / APP_NAME
    else:
        path = Path.home() / ".local" / "share" / "shaher"
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return data_dir() / DB_FILENAME


def backups_dir() -> Path:
    path = data_dir() / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def font_path() -> Path:
    return project_root() / "assets" / "fonts" / "IBMPlexSansArabic-Regular.ttf"


def font_bold_path() -> Path:
    return project_root() / "assets" / "fonts" / "IBMPlexSansArabic-Bold.ttf"
