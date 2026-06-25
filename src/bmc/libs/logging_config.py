"""Application logging: console plus rotating file under ``logs/``."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from bmc.config.settings import McpServerSettings


def root_level(settings: McpServerSettings) -> int:
    """Map configured log level name to a ``logging`` numeric level.

    Parameters
    ----------
    settings : McpServerSettings
        Server settings containing ``log_level``.

    Returns
    -------
    int
        Numeric level; defaults to ``logging.INFO`` when unknown.
    """
    name = settings.log_level.strip().upper()
    if hasattr(logging, name):
        return int(getattr(logging, name))
    return logging.INFO


def configure_logging(settings: McpServerSettings) -> None:
    """Attach stderr and rotating file handlers to the root logger.

    Parameters
    ----------
    settings : McpServerSettings
        Log level and file path (parent directories are created).
    """
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    level = root_level(settings)

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(level)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8',
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    root.addHandler(stream_handler)
    root.addHandler(file_handler)
