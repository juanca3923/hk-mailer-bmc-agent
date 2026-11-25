"""Loggers para AgentForge.

`core_logger`: logs de aplicación (DEBUG..ERROR); propaga al logger raíz, que escribe a archivo y consola.
`user_logger`: mensajes pensados para el usuario, hacia consola (formato mínimo).
"""

from __future__ import annotations

import logging
from pathlib import Path

from config.settings import Settings
from constants.config import LEVELS

settings = Settings.load()


level = LEVELS.get(str(settings.log_level).upper(), logging.INFO)

log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"agent_{settings.agent_slug}.log"

file_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
console_formatter = logging.Formatter("%(message)s")

file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setLevel(level)
file_handler.setFormatter(file_formatter)

# File and console handlers live on the root logger so that modules using ``logging.getLogger(__name__)``
# (commons, services, tools) reach the console too, not only the file; ``agent_forge`` propagates to it.
root_console_handler = logging.StreamHandler()
root_console_handler.setLevel(level)
root_console_handler.setFormatter(file_formatter)

root_logger = logging.getLogger()
root_logger.setLevel(level)
root_logger.addHandler(file_handler)
root_logger.addHandler(root_console_handler)

# httpx/httpcore log the full request URL at INFO (query string included: BMC qualifications carry
# email addresses), so they stay at WARNING whatever the application level is.
for _noisy_logger in ("httpx", "httpcore"):
    logging.getLogger(_noisy_logger).setLevel(logging.WARNING)

core_logger = logging.getLogger("agent_forge")
core_logger.setLevel(logging.DEBUG)
core_logger.propagate = True

user_logger = logging.getLogger("agent_forge.user")
user_logger.setLevel(level)

console_handler = logging.StreamHandler()
console_handler.setLevel(level)
console_handler.setFormatter(console_formatter)

user_logger.addHandler(console_handler)
user_logger.propagate = False


def get_logger() -> logging.Logger:
    """Obtiene el logger de aplicación (archivo y consola)."""
    return core_logger


def get_user_logger() -> logging.Logger:
    """Obtiene el logger para mensajes visibles al usuario (consola)."""
    return user_logger
