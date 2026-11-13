"""Contrato del manejador de las operaciones sobre tickets.

Vive aquí y no en ``type_defs/ports`` porque sus miembros son tipos de la capa de servicios y de configuración
(``BmcClient``, ``BmcSettings``); un contrato en ``type_defs`` no puede importar hacia arriba.
"""

from __future__ import annotations

from typing import Protocol

from commons.bmc.multipart_builder import AttachmentPart
from config.bmc_settings import BmcSettings
from services.bmc.api_client import BmcClient
from type_defs.models.bmc.outputs import BaseOutput


class TicketHandlerContext(Protocol):
    """Minimal handler surface used by incident operations."""

    @property
    def client(self) -> BmcClient:
        """BMC HTTP client."""

    @property
    def settings(self) -> BmcSettings:
        """BMC settings."""

    def ensure_write_allowed(self) -> BaseOutput | None:
        """Return error output when writes are disabled."""

    def load_attachment(self, file_path: str) -> AttachmentPart:
        """Load attachment from disk."""
