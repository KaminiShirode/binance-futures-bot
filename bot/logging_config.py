"""Set up logging — file handler for full debug logs, console for clean output."""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(log_dir: str = "logs", level: int = logging.DEBUG) -> logging.Logger:
    """
    Two handlers:
    - file: DEBUG level, full structured logs with timestamps
    - console: INFO level, clean readable output

    Each run creates a new timestamped file so nothing gets overwritten.
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"trading_bot_{timestamp}.log"

    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)

    # avoid duplicate handlers if called more than once
    if logger.handlers:
        return logger

    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(file_fmt)

    console_fmt = logging.Formatter(fmt="%(levelname)-8s %(message)s")
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(console_fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("logging initialised -> %s", log_file)
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the trading_bot namespace."""
    return logging.getLogger(f"trading_bot.{name}")
