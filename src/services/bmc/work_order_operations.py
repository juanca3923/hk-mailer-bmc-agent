"""Work order write operations shared by agent tools."""

import logging
from collections.abc import Awaitable, Callable
from typing import Protocol

from commons.bmc.entry_values_mapper import EntryValuesMapper
from commons.bmc.guarded_write import run_guarded_write, work_log_fields
from commons.bmc.multipart_builder import AttachmentPart, MultipartBuilder
from commons.bmc.ticket_guards import (
    TicketState,
    require_submitter,
    resolve_ticket_state_from_search,
)
from config.bmc_settings import BmcSettings
from constants.bmc import (
    DEFAULT_WORK_ORDER_CLOSE_FINAL_STATUS,
    DEFAULT_WORK_ORDER_CLOSE_INTERMEDIATE_STATUS,
    DEFAULT_WORK_ORDER_CLOSE_OWNERSHIP_DESCRIPTION,
    DEFAULT_WORK_ORDER_UPDATE_STATUS,
    USER_ERROR_MESSAGE_WORK_ORDER_NOT_FOUND,
    USER_ERROR_MESSAGE_WORK_ORDER_REQUEST_ID_MISSING,
    WORK_LOG_ATTACHMENT_MARKER,
)
from services.bmc.api_client import BmcClient
from type_defs.models.bmc.ar_values import (
    CloseWorkOrderValues,
    UpdateWorkOrderStatusValues,
    WorkInfoWorkOrderValues,
)
from type_defs.models.bmc.inputs import (
    AddWorkOrderAttachmentInput,
    AddWorkOrderNoteInput,
    CloseWorkOrderInput,
    UpdateWorkOrderStatusInput,
)
from type_defs.models.bmc.outputs import BaseOutput

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
        return await resolve_ticket_state_from_search(
            self._handler.client.search_work_order(work_order_id),
            not_found_message=USER_ERROR_MESSAGE_WORK_ORDER_NOT_FOUND.format(work_order_id=work_order_id),
            request_id_missing_message=USER_ERROR_MESSAGE_WORK_ORDER_REQUEST_ID_MISSING,
        )

    async def _guarded_write(
        self,
        work_order_id: str,
        action: Callable[[TicketState], Awaitable[BaseOutput]],
        extra_guard: Callable[[TicketState], BaseOutput | None] | None = None,
    ) -> BaseOutput:
        """Run ``action`` on a work order after the common write guards (see ``run_guarded_write``)."""
        return await run_guarded_write(
            self._handler,
            resolve=lambda: self.resolve_ticket_state(work_order_id),
            missing_message=USER_ERROR_MESSAGE_WORK_ORDER_REQUEST_ID_MISSING,
            action=action,
            extra_guard=extra_guard,
        )

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
        async def post(_state: TicketState) -> BaseOutput:
            values = WorkInfoWorkOrderValues(work_order_id=data.work_order_id, **work_log_fields(data))
            await self._handler.client.post_work_info(MultipartBuilder.build(values))
            logger.info("add_work_order_note ok work_order_id=%s", data.work_order_id)
            return BaseOutput(success=True, message=f"Nota añadida a {data.work_order_id}.")

        return await self._guarded_write(data.work_order_id, post)

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
        async def post(_state: TicketState) -> BaseOutput:
            attachment = self._handler.load_attachment(data.file_path)
            values = WorkInfoWorkOrderValues(
                work_order_id=data.work_order_id,
                attachment_marker=WORK_LOG_ATTACHMENT_MARKER,
                **work_log_fields(data),
            )
            await self._handler.client.post_work_info(MultipartBuilder.build(values, attachment))
            logger.info("add_work_order_attachment ok work_order_id=%s", data.work_order_id)
            return BaseOutput(success=True, message=f"Adjunto añadido a {data.work_order_id}.")

        return await self._guarded_write(data.work_order_id, post)

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
        async def put(state: TicketState) -> BaseOutput:
            values = UpdateWorkOrderStatusValues(description=data.description, status=data.status)
            await self._handler.client.update_work_order(state.request_id, EntryValuesMapper.wrap_entry_body(values))
            return BaseOutput(success=True, message=f"Estado actualizado para {data.work_order_id}.")

        return await self._guarded_write(data.work_order_id, put)

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
        async def close_flow(state: TicketState) -> BaseOutput:
            assignee = self._handler.settings.assignee_display_name
            client = self._handler.client
            ownership = UpdateWorkOrderStatusValues(
                description=DEFAULT_WORK_ORDER_CLOSE_OWNERSHIP_DESCRIPTION,
                status=DEFAULT_WORK_ORDER_UPDATE_STATUS,
                aschg=assignee,
            )
            await client.update_work_order(state.request_id, EntryValuesMapper.wrap_entry_body(ownership))
            intermediate = UpdateWorkOrderStatusValues(
                description=data.intermediate_description,
                status=DEFAULT_WORK_ORDER_CLOSE_INTERMEDIATE_STATUS,
                aschg=assignee,
            )
            await client.update_work_order(state.request_id, EntryValuesMapper.wrap_entry_body(intermediate))
            await self._post_close_note(data.work_order_id, data.intermediate_description)
            close_values = CloseWorkOrderValues(
                description=data.final_description,
                status=DEFAULT_WORK_ORDER_CLOSE_FINAL_STATUS,
            )
            await client.update_work_order(state.request_id, EntryValuesMapper.wrap_entry_body(close_values))
            await self._post_close_note(data.work_order_id, data.final_description)
            logger.info("close_work_order ok work_order_id=%s", data.work_order_id)
            return BaseOutput(success=True, message=f"Orden de trabajo {data.work_order_id} cerrada.")

        return await self._guarded_write(
            data.work_order_id,
            close_flow,
            extra_guard=lambda state: require_submitter(state.submitter, self._handler.settings.username),
        )
