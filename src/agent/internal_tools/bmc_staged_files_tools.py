"""LangChain tool that attaches staged files (shared folder) to an Incident or Work Order.

Shares the lazy ``BaseToolHandler`` singleton via ``services.bmc.tool_handler.get_shared_handler()``,
like the other ``bmc_*_tools`` modules. The agent only handles a ``staging_id``: the file bytes are
read by code from the shared folder and never enter an LLM context.
"""

from __future__ import annotations

import logging
from typing import Annotated, Literal

from langchain_core.tools import tool
from pydantic import Field

from services.bmc import tool_handler
from services.bmc.incident_operations import IncidentOperations
from services.bmc.staged_files import StagedFilesAttacher
from services.bmc.work_order_operations import WorkOrderOperations
from type_defs.models.bmc.inputs import (
    AddIncidentAttachmentInput,
    AddIncidentNoteInput,
    AddWorkOrderAttachmentInput,
    AddWorkOrderNoteInput,
)
from type_defs.models.bmc.outputs import BaseOutput
from type_defs.ports.bmc import TicketWriter

logger = logging.getLogger(__name__)


class IncidentTicketWriter:
    """``TicketWriter`` bound to one Incident (``HPD:WorkLog``)."""

    def __init__(self, operations: IncidentOperations, incident_number: str) -> None:
        self._operations = operations
        self._incident_number = incident_number

    async def attach(self, file_path: str, note_text: str) -> BaseOutput:
        """Upload ``file_path`` as an Incident work log entry."""
        return await self._operations.add_attachment(
            AddIncidentAttachmentInput(incident_number=self._incident_number, note_text=note_text, file_path=file_path),
        )

    async def note(self, note_text: str) -> BaseOutput:
        """Add a note to the Incident work log."""
        return await self._operations.add_note(
            AddIncidentNoteInput(incident_number=self._incident_number, note_text=note_text),
        )


class WorkOrderTicketWriter:
    """``TicketWriter`` bound to one Work Order (``WOI:WorkInfo``)."""

    def __init__(self, operations: WorkOrderOperations, work_order_id: str) -> None:
        self._operations = operations
        self._work_order_id = work_order_id

    async def attach(self, file_path: str, note_text: str) -> BaseOutput:
        """Upload ``file_path`` as a Work Order work info entry."""
        return await self._operations.add_attachment(
            AddWorkOrderAttachmentInput(work_order_id=self._work_order_id, note_text=note_text, file_path=file_path),
        )

    async def note(self, note_text: str) -> BaseOutput:
        """Add a note to the Work Order work info."""
        return await self._operations.add_note(
            AddWorkOrderNoteInput(work_order_id=self._work_order_id, note_text=note_text),
        )


@tool(
    description=(
        "Attach to an existing Incident or Work Order the files staged for it by the email agent "
        "(the original email as .eml plus evidence files). Each file becomes its own entry in the "
        "ticket's activity log; files over the size limit are skipped and listed in a ticket note. "
        "Returns a JSON report of what was attached, skipped or failed. Fails if the ticket is "
        "already closed or writes are disabled."
    )
)
async def bmc_attach_staged_files(
    ticket_type: Annotated[
        Literal["incident", "work_order"],
        Field(description="Kind of ticket the files belong to."),
    ],
    ticket_number: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Incident Number (e.g. INC000000002106) or Work Order ID (e.g. WO0000000000228), "
                "matching ticket_type."
            ),
        ),
    ],
    staging_id: Annotated[
        str,
        Field(
            min_length=1,
            description="Identifier of the staged files, exactly as given in the request that asked to attach them.",
        ),
    ],
) -> str:
    """Attach the files staged under ``staging_id`` to an Incident or Work Order.

    Returns
    -------
    str
        JSON with ``success`` and ``message`` (a JSON report with ``attached``, ``skipped`` and
        ``failed`` on success, or the error text).
    """
    handler = tool_handler.get_shared_handler()
    writer: TicketWriter
    if ticket_type == "incident":
        writer = IncidentTicketWriter(IncidentOperations(handler), ticket_number)
    else:
        writer = WorkOrderTicketWriter(WorkOrderOperations(handler), ticket_number)
    attacher = StagedFilesAttacher(
        writer,
        base_dir=handler.settings.attachment_base_dir,
        max_bytes=handler.settings.max_attachment_bytes,
    )
    result = await attacher.attach(staging_id)
    logger.info("bmc_attach_staged_files %s success=%s", ticket_type, result.success)
    return result.model_dump_json()
