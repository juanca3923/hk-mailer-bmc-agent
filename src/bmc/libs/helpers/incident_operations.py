"""Incident write operations shared by MCP tools."""

import logging
from typing import Protocol

from bmc.exceptions.mcp import MCPClientError
from bmc.libs.api_client import BmcClient
from bmc.libs.constants import (
    AR_FIELD_REQUEST_ID,
    USER_ERROR_MESSAGE_INCIDENT_NOT_FOUND,
    USER_ERROR_MESSAGE_INCIDENT_REQUEST_ID_MISSING,
    WORK_LOG_ATTACHMENT_MARKER,
)
from bmc.libs.helpers.entry_values_mapper import EntryValuesMapper
from bmc.libs.helpers.multipart_builder import AttachmentPart, MultipartBuilder
from bmc.type_defs.ar_values import (
    CloseIncidentValues,
    UpdateIncidentStatusValues,
    WorkInfoIncidentValues,
)
from bmc.type_defs.inputs import AddIncidentAttachmentInput, CloseIncidentInput
from bmc.type_defs.outputs import BaseOutput

logger = logging.getLogger(__name__)


class IncidentHandlerContext(Protocol):
    """Minimal handler surface used by incident operations."""

    @property
    def client(self) -> BmcClient:
        """BMC HTTP client."""

    def ensure_write_allowed(self) -> BaseOutput | None:
        """Return error output when writes are disabled."""

    def load_attachment(self, file_path: str) -> AttachmentPart:
        """Load attachment from disk."""


class IncidentOperations:
    """Resolve incidents and run multi-step BMC write flows."""

    def __init__(self, handler: IncidentHandlerContext) -> None:
        self._handler = handler

    async def resolve_request_id(self, incident_number: str) -> tuple[str | None, BaseOutput | None]:
        """Look up Request ID for an Incident Number.

        Parameters
        ----------
        incident_number : str
            Incident Number to search.

        Returns
        -------
        tuple[str | None, BaseOutput | None]
            ``(request_id, None)`` on success; ``(None, error_output)`` on failure.
        """
        request_id: str | None = None
        error: BaseOutput | None = None
        try:
            search = await self._handler.client.search_incident(incident_number)
            first = search.first_values()
            if first is None:
                message = USER_ERROR_MESSAGE_INCIDENT_NOT_FOUND.format(incident_number=incident_number)
                error = BaseOutput(success=False, message=message)
            else:
                resolved = first.get_str(AR_FIELD_REQUEST_ID)
                if resolved:
                    request_id = resolved
                else:
                    error = BaseOutput(
                        success=False,
                        message=USER_ERROR_MESSAGE_INCIDENT_REQUEST_ID_MISSING,
                    )
        except MCPClientError as exc:
            error = BaseOutput(success=False, message=exc.message)
        return request_id, error

    async def add_attachment(self, data: AddIncidentAttachmentInput) -> BaseOutput:
        """Post a work log with file attachment.

        Parameters
        ----------
        data : AddIncidentAttachmentInput
            Validated tool input.

        Returns
        -------
        BaseOutput
            Success or error output for the MCP tool.
        """
        blocked = self._handler.ensure_write_allowed()
        if blocked is not None:
            return blocked

        output: BaseOutput
        try:
            attachment = self._handler.load_attachment(data.file_path)
            values = WorkInfoIncidentValues(
                incident_number=data.incident_number,
                work_log_type=data.work_log_type,
                view_access=data.view_access,
                secure_work_log=data.secure_work_log,
                detailed_description=data.note_text,
                attachment_marker=WORK_LOG_ATTACHMENT_MARKER,
            )
            work_info_body = MultipartBuilder.build(values, attachment)
            await self._handler.client.post_work_info(work_info_body)
            logger.info('add_incident_attachment ok incident_number=%s', data.incident_number)
            output = BaseOutput(success=True, message=f'Adjunto añadido a {data.incident_number}.')
        except MCPClientError as exc:
            output = BaseOutput(success=False, message=exc.message)
        return output

    async def close(self, data: CloseIncidentInput) -> BaseOutput:
        """Close an incident via optional intermediate and final PUT.

        Parameters
        ----------
        data : CloseIncidentInput
            Validated tool input.

        Returns
        -------
        BaseOutput
            Success or error output for the MCP tool.
        """
        blocked = self._handler.ensure_write_allowed()
        if blocked is not None:
            return blocked

        request_id, error = await self.resolve_request_id(data.incident_number)
        if error is not None:
            return error

        output: BaseOutput
        try:
            if data.intermediate_status:
                intermediate = UpdateIncidentStatusValues(
                    description=data.intermediate_description,
                    status=data.intermediate_status,
                )
                await self._handler.client.update_incident(
                    request_id,
                    EntryValuesMapper.wrap_entry_body(intermediate),
                )
            close_values = CloseIncidentValues(
                description=data.description,
                resolution=data.resolution,
                status=data.final_status,
                status_reason=data.status_reason,
            )
            await self._handler.client.update_incident(
                request_id,
                EntryValuesMapper.wrap_entry_body(close_values),
            )
            logger.info('close_incident ok incident_number=%s', data.incident_number)
            output = BaseOutput(success=True, message=f'Incidente {data.incident_number} cerrado.')
        except MCPClientError as exc:
            output = BaseOutput(success=False, message=exc.message)
        return output
