"""The root logger writes to the console, so modules using ``logging.getLogger(__name__)`` are visible."""

from __future__ import annotations

import logging

from config import logger as logger_module


def test_root_logger_has_a_console_handler() -> None:
    handlers = logging.getLogger().handlers

    assert logger_module.root_console_handler in handlers


def test_application_logger_does_not_duplicate_the_console_handler() -> None:
    own_handlers = logger_module.core_logger.handlers

    assert not [h for h in own_handlers if isinstance(h, logging.StreamHandler)]
