import logging
from logging.handlers import RotatingFileHandler

from app import config


def setup_logging(level=logging.INFO) -> None:
    """Log to a small rotating file in the data folder (never to the network)."""
    root = logging.getLogger("shaher")
    if root.handlers:
        return
    root.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        fh = RotatingFileHandler(config.logs_dir() / "shaher.log", maxBytes=200_000, backupCount=2, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except OSError:
        pass  # logging must never stop the app from starting
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(sh)
