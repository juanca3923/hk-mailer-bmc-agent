"""Base helpers for MCP tool handlers."""

import functools
import logging
from pathlib import Path

from commons.bmc.multipart_builder import AttachmentPart
from commons.bmc.toon_encoder import ToonResponseEncoder
from config.bmc_settings import BmcSettings
from constants.bmc.messages import (
    USER_ERROR_MESSAGE_ATTACHMENT_NOT_ALLOWED,
    USER_ERROR_MESSAGE_ATTACHMENT_NOT_CONFIGURED,
    USER_ERROR_MESSAGE_ATTACHMENT_NOT_FOUND,
    USER_ERROR_MESSAGE_ATTACHMENT_TOO_LARGE,
    USER_ERROR_MESSAGE_WRITE_DISABLED,
)
from exception.mcp import MCPClientError
from services.bmc.api_client import BmcClient
from type_defs.models.bmc.outputs import BaseOutput


class BaseToolHandler:
    """Shared dependencies and utilities for BMC MCP tools.

    Attributes
    ----------
    _settings : BmcSettings
        Runtime BMC and MCP configuration.
    _client : BmcClient
        Authenticated BMC HTTP client.
    _logger : logging.Logger
        Module logger for tool handlers.
    """

    def __init__(
        self,
        client: BmcClient | None = None,
        settings: BmcSettings | None = None,
    ) -> None:
        self._settings = settings or BmcSettings()
        self._client = client or BmcClient(self._settings)
        self._logger = logging.getLogger(self.__class__.__module__)

    @property
    def settings(self) -> BmcSettings:
        """Return the BMC settings used by tools.

        Returns
        -------
        BmcSettings
            Runtime BMC and MCP configuration.
        """
        return self._settings

    @property
    def client(self) -> BmcClient:
        """Return the BMC HTTP client used by tools.

        Returns
        -------
        BmcClient
            Shared async client with session from ``BmcConnectionManager``.
        """
        return self._client

    def ensure_write_allowed(self) -> BaseOutput | None:
        """Block mutating tools when writes are disabled in settings.

        Returns
        -------
        BaseOutput | None
            Error ``BaseOutput`` when ``allow_write`` is false; otherwise ``None``.
        """
        if not self._settings.allow_write:
            return BaseOutput(success=False, message=USER_ERROR_MESSAGE_WRITE_DISABLED)
        return None

    @staticmethod
    def failure(exc: MCPClientError) -> BaseOutput:
        """Map a client error to a failed tool ``BaseOutput``.

        Parameters
        ----------
        exc : MCPClientError
            Error raised by the BMC client layer.

        Returns
        -------
        BaseOutput
            ``success=False`` with the user-facing message from ``exc``.
        """
        return BaseOutput(success=False, message=exc.message)

    @staticmethod
    def success_toon(data: object) -> BaseOutput:
        """Encode structured data as TOON in a successful ``BaseOutput``.

        Parameters
        ----------
        data : object
            Pydantic model, ``dict``, or value stringified when unsupported.

        Returns
        -------
        BaseOutput
            ``success=True`` with TOON-encoded ``message`` when possible.
        """
        if hasattr(data, 'model_dump'):
            message = ToonResponseEncoder.encode_model(data)  # type: ignore[arg-type]
        elif isinstance(data, dict):
            message = ToonResponseEncoder.encode(data)
        else:
            message = str(data)
        return BaseOutput(success=True, message=message)

    def load_attachment(self, file_path: str) -> AttachmentPart:
        """Load and validate an attachment from disk.

        Only files inside ``attachment_base_dir`` are readable: the path is fully resolved
        (``..`` and symlinks included) before checking it, so neither traversal nor a link
        planted inside the folder can reach other files of the host.

        Parameters
        ----------
        file_path : str
            Path to the file to attach.

        Returns
        -------
        AttachmentPart
            Validated attachment ready for multipart upload.

        Raises
        ------
        MCPClientError
            If attachments are not configured, the file is outside ``attachment_base_dir``,
            it is missing, or it exceeds ``max_attachment_bytes``.
        """
        base_dir = self._settings.attachment_base_dir
        if base_dir is None:
            raise MCPClientError(USER_ERROR_MESSAGE_ATTACHMENT_NOT_CONFIGURED, status_code=None)
        path = Path(file_path).resolve()
        if not path.is_relative_to(base_dir.resolve()):
            self._logger.warning("Attachment rejected, outside base dir: %s", file_path)
            raise MCPClientError(USER_ERROR_MESSAGE_ATTACHMENT_NOT_ALLOWED, status_code=None)
        if not path.is_file():
            msg = USER_ERROR_MESSAGE_ATTACHMENT_NOT_FOUND
            raise MCPClientError(msg, status_code=None)
        size = path.stat().st_size
        if size > self._settings.max_attachment_bytes:
            raise MCPClientError(USER_ERROR_MESSAGE_ATTACHMENT_TOO_LARGE, status_code=None)
        return AttachmentPart.from_path(path)


@functools.cache
def get_shared_handler() -> BaseToolHandler:
    """Return the process-wide handler, initializing it on first access.

    Shared by every ``agent.internal_tools.bmc_*`` module (split across several files
    to stay under the repo's line-count limit) so they all validate settings and hold
    one BMC session, instead of one per module. Idempotency is provided by
    ``functools.cache`` (a niladic function, so it runs its body only on the first
    call and returns the cached instance on every call after), instead of a
    module-level flag.

    Returns
    -------
    BaseToolHandler
        Singleton handler backed by ``BmcSettings`` from environment.
    """
    return BaseToolHandler()
