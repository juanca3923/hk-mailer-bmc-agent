"""Work order write operations shared by MCP tools."""

import logging
from typing import Protocol

from bmc.config.settings import BmcSettings
from bmc.exceptions.mcp import MCPClientError
from bmc.libs.api_client import BmcClient
from bmc.libs.constants import (
    AR_FIELD_REQUEST_ID,
    DEFAULT_WORK_ORDER_CLOSE_INTERMEDIATE_STATUS,
    USER_ERROR_MESSAGE_WORK_ORDER_NOT_FOUND,
    USER_ERROR_MESSAGE_WORK_ORDER_REQUEST_ID_MISSING,
    WORK_LOG_ATTACHMENT_MARKER,
)
from bmc.libs.helpers.entry_values_mapper import EntryValuesMapper
from bmc.libs.helpers.multipart_builder import AttachmentPart, MultipartBuilder
from bmc.type_defs.ar_values import (
    CloseWorkOrderValues,
    UpdateWorkOrderStatusValues,
    WorkInfoWorkOrderValues,
)
from bmc.type_defs.inputs import (
    AddWorkOrderAttachmentInput,
    CloseWorkOrderInput,
    UpdateWorkOrderStatusInput,
)
from bmc.type_defs.outputs import BaseOutput

logger = logging.getLogger(__name__)


class WorkOrderHandlerContext(Protocol):
    """Minimal handler surface used by work order operations."""

    @property
    def client(self) -> BmcClient:
        """BMC HTTP client."""

    def ensure_write_allowed(self) -> BaseOutput | None:
        """Return error output when writes are disabled."""

    def load_attachment(self, file_path: str) -> AttachmentPart:
        """Load attachment from disk."""


class WorkOrderOperations:
    """Resolve work orders and run multi-step BMC write flows."""

    def __init__(self, handler: WorkOrderHandlerContext) -> None:
        self._handler = handler

    async def resolve_request_id(self, work_order_id: str) -> tuple[str | None, BaseOutput | None]:
        """Look up Request ID for a Work Order ID.

        Parameters
        ----------
        work_order_id : str
            Work Order ID to search.

        Returns
        -------
        tuple[str | None, BaseOutput | None]
            ``(request_id, None)`` on success; ``(None, error_output)`` on failure.
        """
        request_id: str | None = None
        error: BaseOutput | None = None
        try:
            search = await self._handler.client.search_work_order(work_order_id)
            first = search.first_values()
            if first is None:
                message = USER_ERROR_MESSAGE_WORK_ORDER_NOT_FOUND.format(work_order_id=work_order_id)
                error = BaseOutput(success=False, message=message)
            else:
                resolved = first.get_str(AR_FIELD_REQUEST_ID)
                if resolved:
                    request_id = resolved
                else:
                    error = BaseOutput(
                        success=False,
                        message=USER_ERROR_MESSAGE_WORK_ORDER_REQUEST_ID_MISSING,
                    )
        except MCPClientError as exc:
            error = BaseOutput(success=False, message=exc.message)
        return request_id, error

    async def add_attachment(self, data: AddWorkOrderAttachmentInput) -> BaseOutput:
        """Post a work log with file attachment.

        Parameters
        ----------
        data : AddWorkOrderAttachmentInput
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
            values = WorkInfoWorkOrderValues(
                work_order_id=data.work_order_id,
                work_log_type=data.work_log_type,
                view_access=data.view_access,
                secure_work_log=data.secure_work_log,
                detailed_description=data.note_text,
                attachment_marker=WORK_LOG_ATTACHMENT_MARKER,
            )
            work_info_body = MultipartBuilder.build(values, attachment)
            await self._handler.client.post_work_info(work_info_body)
            logger.info('add_work_order_attachment ok work_order_id=%s', data.work_order_id)
            output = BaseOutput(success=True, message=f'Adjunto añadido a {data.work_order_id}.')
        except MCPClientError as exc:
            output = BaseOutput(success=False, message=exc.message)
        return output

    async def update_status(self, data: UpdateWorkOrderStatusInput) -> BaseOutput:
        """PUT work order status using Request ID from search.

        Parameters
        ----------
        data : UpdateWorkOrderStatusInput
            Validated tool input.

        Returns
        -------
        BaseOutput
            Success or error output for the MCP tool.
        """
        blocked = self._handler.ensure_write_allowed()
        if blocked is not None:
            return blocked

        request_id, error = await self.resolve_request_id(data.work_order_id)
        if error is not None:
            return error

        output: BaseOutput
        try:
            values = UpdateWorkOrderStatusValues(
                description=data.description,
                status=data.status,
            )
            body = EntryValuesMapper.wrap_entry_body(values)
            await self._handler.client.update_work_order(request_id, body)
            output = BaseOutput(success=True, message=f'Estado actualizado para {data.work_order_id}.')
        except MCPClientError as exc:
            output = BaseOutput(success=False, message=exc.message)
        return output

    async def close(self, data: CloseWorkOrderInput) -> BaseOutput:
        """Close a work order: PUT Completed+Assignee, then PUT Closed.

        Parameters
        ----------
        data : CloseWorkOrderInput
            Validated tool input.

        Returns
        -------
        BaseOutput
            Success or error output for the MCP tool.
        """
        blocked = self._handler.ensure_write_allowed()
        if blocked is not None:
            return blocked

        request_id, error = await self.resolve_request_id(data.work_order_id)
        if error is not None:
            return error

        output: BaseOutput
        try:
            intermediate = UpdateWorkOrderStatusValues(
                description=data.intermediate_description,
                status=DEFAULT_WORK_ORDER_CLOSE_INTERMEDIATE_STATUS,
                assignee=BmcSettings().username,
            )
            await self._handler.client.update_work_order(
                request_id,
                EntryValuesMapper.wrap_entry_body(intermediate),
            )
            close_values = CloseWorkOrderValues(
                description=data.final_description,
                status=data.final_status,
                status_reason=data.status_reason,
            )
            await self._handler.client.update_work_order(
                request_id,
                EntryValuesMapper.wrap_entry_body(close_values),
            )
            logger.info('close_work_order ok work_order_id=%s', data.work_order_id)
            output = BaseOutput(success=True, message=f'Orden de trabajo {data.work_order_id} cerrada.')
        except MCPClientError as exc:
            output = BaseOutput(success=False, message=exc.message)
        return output
