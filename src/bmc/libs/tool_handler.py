"""Base helpers for MCP tool handlers."""

import logging
from pathlib import Path

from bmc.config.settings import BmcSettings
from bmc.exceptions.mcp import MCPClientError
from bmc.libs.api_client import BmcClient
from bmc.libs.constants import (
    USER_ERROR_MESSAGE_ATTACHMENT_NOT_FOUND,
    USER_ERROR_MESSAGE_ATTACHMENT_TOO_LARGE,
    USER_ERROR_MESSAGE_WRITE_DISABLED,
)
from bmc.libs.helpers.multipart_builder import AttachmentPart
from bmc.libs.toon_encoder import ToonResponseEncoder
from bmc.type_defs.outputs import BaseOutput


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
            message = ToonResponseEncoder.encode(data)  # type: ignore[arg-type]
        else:
            message = str(data)
        return BaseOutput(success=True, message=message)

    def load_attachment(self, file_path: str) -> AttachmentPart:
        """Load and validate an attachment from disk.

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
            If the file is missing or exceeds ``max_attachment_bytes``.
        """
        path = Path(file_path)
        if not path.is_file():
            msg = USER_ERROR_MESSAGE_ATTACHMENT_NOT_FOUND
            raise MCPClientError(msg, status_code=None)
        size = path.stat().st_size
        if size > self._settings.max_attachment_bytes:
            raise MCPClientError(USER_ERROR_MESSAGE_ATTACHMENT_TOO_LARGE, status_code=None)
        return AttachmentPart.from_path(path)
