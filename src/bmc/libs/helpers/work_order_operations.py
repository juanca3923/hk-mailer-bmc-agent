"""Work order write operations shared by agent tools."""

import logging
from typing import Protocol

from bmc.config.settings import BmcSettings
from bmc.exceptions.mcp import MCPClientError
from bmc.libs.api_client import BmcClient
from bmc.libs.constants import (
    AR_FIELD_REQUEST_ID,
    AR_FIELD_STATUS,
    AR_FIELD_SUBMITTER,
    DEFAULT_WORK_ORDER_CLOSE_FINAL_STATUS,
    DEFAULT_WORK_ORDER_CLOSE_INTERMEDIATE_STATUS,
    DEFAULT_WORK_ORDER_CLOSE_OWNERSHIP_DESCRIPTION,
    DEFAULT_WORK_ORDER_UPDATE_STATUS,
    USER_ERROR_MESSAGE_WORK_ORDER_NOT_FOUND,
    USER_ERROR_MESSAGE_WORK_ORDER_REQUEST_ID_MISSING,
    WORK_LOG_ATTACHMENT_MARKER,
)
from bmc.libs.helpers.entry_values_mapper import EntryValuesMapper
from bmc.libs.helpers.multipart_builder import AttachmentPart, MultipartBuilder
from bmc.libs.helpers.ticket_guards import (
    TicketState,
    require_not_closed,
    require_submitter,
)
from bmc.type_defs.ar_values import (
    CloseWorkOrderValues,
    UpdateWorkOrderStatusValues,
    WorkInfoWorkOrderValues,
)
from bmc.type_defs.inputs import (
    AddWorkOrderAttachmentInput,
    AddWorkOrderNoteInput,
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

    @property
    def settings(self) -> BmcSettings:
        """BMC settings."""

    def ensure_write_allowed(self) -> BaseOutput | None:
        """Return error output when writes are disabled."""

    def load_attachment(self, file_path: str) -> AttachmentPart:
        """Load attachment from disk."""


class WorkOrderOperations:
    """Resolve work orders and run multi-step BMC write flows."""

    def __init__(self, handler: WorkOrderHandlerContext) -> None:
        self._handler = handler

    async def resolve_ticket_state(self, work_order_id: str) -> tuple[TicketState | None, BaseOutput | None]:
        """Look up Request ID, Status, and Submitter for a Work Order ID.

        Parameters
        ----------
        work_order_id : str
            Work Order ID to search.

        Returns
        -------
        tuple[TicketState | None, BaseOutput | None]
            ``(state, None)`` on success; ``(None, error_output)`` on failure.
        """
        state: TicketState | None = None
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
                    state = TicketState(
                        request_id=resolved,
                        status=first.get_str(AR_FIELD_STATUS),
                        submitter=first.get_str(AR_FIELD_SUBMITTER),
                    )
                else:
                    error = BaseOutput(
                        success=False,
                        message=USER_ERROR_MESSAGE_WORK_ORDER_REQUEST_ID_MISSING,
                    )
        except MCPClientError as exc:
            error = BaseOutput(success=False, message=exc.message)
        return state, error

    async def add_note(self, data: AddWorkOrderNoteInput) -> BaseOutput:
        """Post a work log note without attachment, after guard checks.

        Parameters
        ----------
        data : AddWorkOrderNoteInput
            Validated tool input.

        Returns
        -------
        BaseOutput
            Success or error output for the tool.
        """
        blocked = self._handler.ensure_write_allowed()
        if blocked is not None:
            return blocked

        state, error = await self.resolve_ticket_state(data.work_order_id)
        if error is not None or state is None:
            return error or BaseOutput(success=False, message=USER_ERROR_MESSAGE_WORK_ORDER_REQUEST_ID_MISSING)

        output = require_not_closed(state.status)
        if output is None:
            try:
                values = WorkInfoWorkOrderValues(
                    work_order_id=data.work_order_id,
                    work_log_type=data.work_log_type,
                    view_access=data.view_access,
                    secure_work_log=data.secure_work_log,
                    detailed_description=data.note_text,
                )
                work_info_body = MultipartBuilder.build(values)
                await self._handler.client.post_work_info(work_info_body)
                logger.info("add_work_order_note ok work_order_id=%s", data.work_order_id)
                output = BaseOutput(success=True, message=f"Nota añadida a {data.work_order_id}.")
            except MCPClientError as exc:
                output = BaseOutput(success=False, message=exc.message)
        return output

    async def add_attachment(self, data: AddWorkOrderAttachmentInput) -> BaseOutput:
        """Post a work log with file attachment, after guard checks.

        Parameters
        ----------
        data : AddWorkOrderAttachmentInput
            Validated tool input.

        Returns
        -------
        BaseOutput
            Success or error output for the tool.
        """
        blocked = self._handler.ensure_write_allowed()
        if blocked is not None:
            return blocked

        state, error = await self.resolve_ticket_state(data.work_order_id)
        if error is not None or state is None:
            return error or BaseOutput(success=False, message=USER_ERROR_MESSAGE_WORK_ORDER_REQUEST_ID_MISSING)

        output = require_not_closed(state.status)
        if output is None:
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
                logger.info("add_work_order_attachment ok work_order_id=%s", data.work_order_id)
                output = BaseOutput(success=True, message=f"Adjunto añadido a {data.work_order_id}.")
            except MCPClientError as exc:
                output = BaseOutput(success=False, message=exc.message)
        return output

    async def update_status(self, data: UpdateWorkOrderStatusInput) -> BaseOutput:
        """PUT work order status using Request ID from search, after guard checks.

        Parameters
        ----------
        data : UpdateWorkOrderStatusInput
            Validated tool input.

        Returns
        -------
        BaseOutput
            Success or error output for the tool.
        """
        blocked = self._handler.ensure_write_allowed()
        if blocked is not None:
            return blocked

        state, error = await self.resolve_ticket_state(data.work_order_id)
        if error is not None or state is None:
            return error or BaseOutput(success=False, message=USER_ERROR_MESSAGE_WORK_ORDER_REQUEST_ID_MISSING)

        output = require_not_closed(state.status)
        if output is None:
            try:
                values = UpdateWorkOrderStatusValues(
                    description=data.description,
                    status=data.status,
                )
                body = EntryValuesMapper.wrap_entry_body(values)
                await self._handler.client.update_work_order(state.request_id, body)
                output = BaseOutput(success=True, message=f"Estado actualizado para {data.work_order_id}.")
            except MCPClientError as exc:
                output = BaseOutput(success=False, message=exc.message)
        return output

    async def _post_close_note(self, work_order_id: str, note_text: str) -> None:
        """Post a work log note documenting one step of the close flow.

        BMC's ``Description`` field on ``WOI:WorkOrderInterface`` doubles as the ticket's
        title, so each PUT of ``close`` overwrites it; a work log note is the only way to
        leave a visible, non-overwritten trail of what happened at each step.

        Parameters
        ----------
        work_order_id : str
            Target Work Order ID.
        note_text : str
            Work log detailed description text.
        """
        values = WorkInfoWorkOrderValues(
            work_order_id=work_order_id,
            detailed_description=note_text,
        )
        work_info_body = MultipartBuilder.build(values)
        await self._handler.client.post_work_info(work_info_body)

    async def close(self, data: CloseWorkOrderInput) -> BaseOutput:
        """Close a work order: PUT ownership+In Progress, then 2x (PUT status + work log note).

        Steps: ownership+In Progress, Completed+ASCHG, Closed. Does not require the ticket
        to already be ``In Progress``: the first PUT takes ownership (``ASCHG``) and moves
        it there. Only rejects tickets already ``Closed`` and tickets not opened by this
        agent's own BMC user (``Submitter``), before issuing any write. The Completed and
        Closed PUTs are each followed by a work log note with the same text, since
        ``Description`` doubles as the ticket's title and gets overwritten by the next
        PUT; the ownership PUT does not get a note because BMC already logs the ``ASCHG``
        change as its own ``Asignado a`` activity entry.

        Parameters
        ----------
        data : CloseWorkOrderInput
            Validated tool input.

        Returns
        -------
        BaseOutput
            Success or error output for the tool.
        """
        blocked = self._handler.ensure_write_allowed()
        if blocked is not None:
            return blocked

        state, error = await self.resolve_ticket_state(data.work_order_id)
        if error is not None or state is None:
            return error or BaseOutput(success=False, message=USER_ERROR_MESSAGE_WORK_ORDER_REQUEST_ID_MISSING)

        output = require_not_closed(state.status) or require_submitter(state.submitter, self._handler.settings.username)
        if output is None:
            try:
                ownership = UpdateWorkOrderStatusValues(
                    description=DEFAULT_WORK_ORDER_CLOSE_OWNERSHIP_DESCRIPTION,
                    status=DEFAULT_WORK_ORDER_UPDATE_STATUS,
                    aschg=self._handler.settings.assignee_display_name,
                )
                await self._handler.client.update_work_order(
                    state.request_id,
                    EntryValuesMapper.wrap_entry_body(ownership),
                )
                intermediate = UpdateWorkOrderStatusValues(
                    description=data.intermediate_description,
                    status=DEFAULT_WORK_ORDER_CLOSE_INTERMEDIATE_STATUS,
                    aschg=self._handler.settings.assignee_display_name,
                )
                await self._handler.client.update_work_order(
                    state.request_id,
                    EntryValuesMapper.wrap_entry_body(intermediate),
                )
                await self._post_close_note(data.work_order_id, data.intermediate_description)
                close_values = CloseWorkOrderValues(
                    description=data.final_description,
                    status=DEFAULT_WORK_ORDER_CLOSE_FINAL_STATUS,
                )
                await self._handler.client.update_work_order(
                    state.request_id,
                    EntryValuesMapper.wrap_entry_body(close_values),
                )
                await self._post_close_note(data.work_order_id, data.final_description)
                logger.info("close_work_order ok work_order_id=%s", data.work_order_id)
                output = BaseOutput(success=True, message=f"Orden de trabajo {data.work_order_id} cerrada.")
            except MCPClientError as exc:
                output = BaseOutput(success=False, message=exc.message)
        return output
