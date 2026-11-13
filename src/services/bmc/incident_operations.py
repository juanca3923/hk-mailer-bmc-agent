"""Incident write operations shared by agent tools."""

import logging
from collections.abc import Awaitable, Callable

from commons.bmc.entry_values_mapper import EntryValuesMapper
from commons.bmc.guarded_write import run_guarded_write, work_log_fields
from commons.bmc.multipart_builder import MultipartBuilder
from commons.bmc.ticket_guards import require_submitter, resolve_ticket_state_from_search
from commons.bmc.toon_encoder import ToonResponseEncoder
from constants.bmc.api import WORK_LOG_ATTACHMENT_MARKER
from constants.bmc.defaults import (
    DEFAULT_COMPANY,
    DEFAULT_INCIDENT_SUPPORT_COMPANY,
    DEFAULT_INCIDENT_SUPPORT_ORGANIZATION,
)
from constants.bmc.fields import (
    AR_FIELD_CATEGORIZATION_TIER_1,
    AR_FIELD_CATEGORIZATION_TIER_2,
    AR_FIELD_INCIDENT_NUMBER,
    AR_FIELD_REQUEST_ID,
)
from constants.bmc.messages import USER_ERROR_MESSAGE_INCIDENT_NOT_FOUND, USER_ERROR_MESSAGE_INCIDENT_REQUEST_ID_MISSING
from constants.bmc.tickets import (
    DEFAULT_INCIDENT_CATEGORIZATION_FALLBACK_NOTE,
    DEFAULT_INCIDENT_CATEGORIZATION_FALLBACK_TIER_1,
    DEFAULT_INCIDENT_CATEGORIZATION_FALLBACK_TIER_2,
    DEFAULT_INCIDENT_CLOSE_FINAL_STATUS,
    DEFAULT_INCIDENT_CLOSE_INTERMEDIATE_STATUS,
    DEFAULT_INCIDENT_CLOSE_OWNERSHIP_DESCRIPTION,
    DEFAULT_INCIDENT_CLOSE_STATUS_REASON,
    INCIDENT_FIXED_IMPACT,
    INCIDENT_FIXED_URGENCY,
)
from exception.mcp import MCPClientError
from services.bmc.handler_context import TicketHandlerContext
from services.bmc.person_lookup import resolve_reporter_identity
from type_defs.models.bmc.ar_api import BmcEntryListResponse
from type_defs.models.bmc.ar_values import (
    CloseIncidentValues,
    CreateIncidentValues,
    UpdateIncidentCategorizationValues,
    UpdateIncidentStatusValues,
    WorkInfoIncidentValues,
)
from type_defs.models.bmc.inputs import (
    AddIncidentAttachmentInput,
    AddIncidentNoteInput,
    CloseIncidentInput,
    CreateIncidentInput,
)
from type_defs.models.bmc.outputs import BaseOutput, IncidentCreatedData
from type_defs.models.bmc.ticket_state import TicketState

logger = logging.getLogger(__name__)


class IncidentOperations:
    """Resolve incidents and run multi-step BMC write flows."""

    def __init__(self, handler: TicketHandlerContext) -> None:
        self._handler = handler

    async def resolve_ticket_state(self, incident_number: str) -> tuple[TicketState | None, BaseOutput | None]:
        """Look up Request ID, Status, and Submitter for an Incident Number.

        Parameters
        ----------
        incident_number : str
            Incident Number to search.

        Returns
        -------
        tuple[TicketState | None, BaseOutput | None]
            ``(state, None)`` on success; ``(None, error_output)`` on failure.
        """
        return await resolve_ticket_state_from_search(
            self._handler.client.search_incident(incident_number),
            not_found_message=USER_ERROR_MESSAGE_INCIDENT_NOT_FOUND.format(incident_number=incident_number),
            request_id_missing_message=USER_ERROR_MESSAGE_INCIDENT_REQUEST_ID_MISSING,
        )

    async def _guarded_write(
        self,
        incident_number: str,
        action: Callable[[TicketState], Awaitable[BaseOutput]],
        extra_guard: Callable[[TicketState], BaseOutput | None] | None = None,
    ) -> BaseOutput:
        """Run ``action`` on an incident after the common write guards (see ``run_guarded_write``)."""
        return await run_guarded_write(
            self._handler,
            resolve=lambda: self.resolve_ticket_state(incident_number),
            missing_message=USER_ERROR_MESSAGE_INCIDENT_REQUEST_ID_MISSING,
            action=action,
            extra_guard=extra_guard,
        )

    async def create(self, data: CreateIncidentInput) -> BaseOutput:
        """Create an incident, then patch the operational category if BMC left it empty.

        Resolves the submitter's real identity from ``data.reporter_email`` via
        ``CTM:People`` first (see ``services.bmc.person_lookup``) and aborts
        without creating anything if that person cannot be found. Otherwise runs
        ``HPD:IncidentInterface_Create`` and immediately searches the created incident
        to check whether ``Categorization Tier 1``/``Categorization Tier 2`` came back
        populated. BMC silently drops some catalog-valid combinations at creation time
        without erroring, leaving the incident uncloseable; when that happens, this reapplies
        a known-working default via a follow-up PUT and leaves a work log note documenting it.
        This is a temporary workaround (see ``DEFAULT_INCIDENT_CATEGORIZATION_FALLBACK_TIER_1``
        in ``bmc/libs/constants.py``), to be removed once BMC/ITSM confirms which combinations
        the creation form accepts.

        Parameters
        ----------
        data : CreateIncidentInput
            Validated tool input.

        Returns
        -------
        BaseOutput
            ``success=True`` with TOON-encoded created ids; ``success=False`` on
            error, including an unresolvable ``reporter_email`` (no ticket created).
        """
        blocked = self._handler.ensure_write_allowed()
        if blocked is not None:
            return blocked
        identity = await resolve_reporter_identity(self._handler.client, data.reporter_email)
        if isinstance(identity, BaseOutput):
            return identity
        values = CreateIncidentValues(
            company=DEFAULT_COMPANY,
            first_name=identity.first_name,
            last_name=identity.last_name,
            description=data.description,
            impact=INCIDENT_FIXED_IMPACT,
            urgency=INCIDENT_FIXED_URGENCY,
            status=data.status,
            reported_source=data.reported_source,
            service_type=data.service_type,
            detailed_decription=data.detailed_decription,
            categorization_tier_1=data.categorization_tier_1,
            categorization_tier_2=data.categorization_tier_2,
            product_categorization_tier_1=data.product_categorization_tier_1,
            product_categorization_tier_2=data.product_categorization_tier_2,
            product_categorization_tier_3=data.product_categorization_tier_3,
            assigned_support_company=DEFAULT_INCIDENT_SUPPORT_COMPANY,
            assigned_support_organization=DEFAULT_INCIDENT_SUPPORT_ORGANIZATION,
            assigned_group=data.assigned_group,
        )
        return await self._create_incident_entry(values)

    async def _create_incident_entry(self, values: CreateIncidentValues) -> BaseOutput:
        """Create the incident entry in BMC, apply the categorization fallback, and build output.

        Parameters
        ----------
        values : CreateIncidentValues
            Mapped AR field values for ``HPD:IncidentInterface_Create``.

        Returns
        -------
        BaseOutput
            ``success=True`` with TOON-encoded created ids; ``success=False`` on error.
        """
        try:
            created = await self._handler.client.create_incident_entry(EntryValuesMapper.wrap_entry_body(values))
        except MCPClientError as exc:
            logger.warning("create_incident failed status_code=%s", exc.status_code)
            return BaseOutput(success=False, message=exc.message)
        incident_number = created.values.get_str(AR_FIELD_INCIDENT_NUMBER)
        fallback_applied = await self._apply_categorization_fallback(incident_number)
        out = IncidentCreatedData(
            incident_number=incident_number,
            description=created.values.get_str("Description"),
            categorization_fallback_applied=fallback_applied,
        )
        logger.info("create_incident ok incident_number=%s", incident_number)
        return BaseOutput(success=True, message=ToonResponseEncoder.encode_model(out))

    async def _search_created_incident(self, incident_number: str) -> BmcEntryListResponse | None:
        """Search a just-created incident, swallowing failures for a best-effort follow-up check.

        Parameters
        ----------
        incident_number : str
            Incident Number just created.

        Returns
        -------
        BmcEntryListResponse | None
            Search result, or ``None`` when the incident could not be searched.
        """
        try:
            return await self._handler.client.search_incident(incident_number)
        except MCPClientError:
            logger.warning("create_incident categorization check failed incident_number=%s", incident_number)
            return None

    async def _find_request_id_with_empty_categorization(self, incident_number: str) -> str | None:
        """Search a just-created incident and return its Request ID if the category is empty.

        Parameters
        ----------
        incident_number : str
            Incident Number just created.

        Returns
        -------
        str | None
            Request ID to patch, or ``None`` when categorization is already populated, the
            incident could not be searched, or Request ID is unavailable.
        """
        search = await self._search_created_incident(incident_number) if incident_number else None
        first = search.first_values() if search is not None else None
        if first is None:
            return None
        has_categorization = first.get_str(AR_FIELD_CATEGORIZATION_TIER_1) and first.get_str(
            AR_FIELD_CATEGORIZATION_TIER_2
        )
        if has_categorization:
            return None
        return first.get_str(AR_FIELD_REQUEST_ID) or None

    async def _apply_categorization_fallback(self, incident_number: str) -> bool:
        """Patch ``Categorization Tier 1``/``Tier 2`` when BMC left them empty after creation.

        Best-effort: the incident was already created successfully by the time this runs, so
        any failure here (search, PUT, or note) is logged and swallowed instead of turned into
        a tool error — the caller already has a usable incident number either way.

        Parameters
        ----------
        incident_number : str
            Incident Number just created.

        Returns
        -------
        bool
            Whether the fallback PUT was applied.
        """
        request_id = await self._find_request_id_with_empty_categorization(incident_number)
        if request_id is None:
            return False
        fallback_values = UpdateIncidentCategorizationValues(
            categorization_tier_1=DEFAULT_INCIDENT_CATEGORIZATION_FALLBACK_TIER_1,
            categorization_tier_2=DEFAULT_INCIDENT_CATEGORIZATION_FALLBACK_TIER_2,
        )
        try:
            await self._handler.client.update_incident(request_id, EntryValuesMapper.wrap_entry_body(fallback_values))
            note_values = WorkInfoIncidentValues(
                incident_number=incident_number,
                detailed_description=DEFAULT_INCIDENT_CATEGORIZATION_FALLBACK_NOTE,
            )
            await self._handler.client.post_incident_work_log(MultipartBuilder.build(note_values))
        except MCPClientError:
            logger.warning("create_incident categorization fallback failed incident_number=%s", incident_number)
            return False
        logger.info("create_incident categorization fallback applied incident_number=%s", incident_number)
        return True

    async def add_note(self, data: AddIncidentNoteInput) -> BaseOutput:
        """Post a work log note without attachment, after guard checks.

        Parameters
        ----------
        data : AddIncidentNoteInput
            Validated tool input.

        Returns
        -------
        BaseOutput
            Success or error output for the tool.
        """
        async def post(_state: TicketState) -> BaseOutput:
            values = WorkInfoIncidentValues(incident_number=data.incident_number, **work_log_fields(data))
            await self._handler.client.post_incident_work_log(MultipartBuilder.build(values))
            logger.info("add_incident_note ok incident_number=%s", data.incident_number)
            return BaseOutput(success=True, message=f"Nota añadida a {data.incident_number}.")

        return await self._guarded_write(data.incident_number, post)

    async def add_attachment(self, data: AddIncidentAttachmentInput) -> BaseOutput:
        """Post a work log with file attachment, after guard checks.

        Parameters
        ----------
        data : AddIncidentAttachmentInput
            Validated tool input.

        Returns
        -------
        BaseOutput
            Success or error output for the tool.
        """
        async def post(_state: TicketState) -> BaseOutput:
            attachment = self._handler.load_attachment(data.file_path)
            values = WorkInfoIncidentValues(
                incident_number=data.incident_number,
                attachment_marker=WORK_LOG_ATTACHMENT_MARKER,
                **work_log_fields(data),
            )
            await self._handler.client.post_incident_work_log(MultipartBuilder.build(values, attachment))
            logger.info("add_incident_attachment ok incident_number=%s", data.incident_number)
            return BaseOutput(success=True, message=f"Adjunto añadido a {data.incident_number}.")

        return await self._guarded_write(data.incident_number, post)

    async def close(self, data: CloseIncidentInput) -> BaseOutput:
        """Close an incident: PUT ownership+In Progress, then PUT close (Resolved).

        Does not require the ticket to already be ``In Progress``: the first PUT takes
        ownership (``Assignee``) and moves it there from any non-``Closed`` status. Only
        rejects tickets already ``Closed`` and tickets not opened by this agent's own BMC
        user (``Submitter``), before issuing any write.

        Parameters
        ----------
        data : CloseIncidentInput
            Validated tool input.

        Returns
        -------
        BaseOutput
            Success or error output for the tool.
        """
        async def close_flow(state: TicketState) -> BaseOutput:
            ownership = UpdateIncidentStatusValues(
                description=DEFAULT_INCIDENT_CLOSE_OWNERSHIP_DESCRIPTION,
                status=DEFAULT_INCIDENT_CLOSE_INTERMEDIATE_STATUS,
                assignee=self._handler.settings.assignee_display_name,
            )
            await self._handler.client.update_incident(state.request_id, EntryValuesMapper.wrap_entry_body(ownership))
            close_values = CloseIncidentValues(
                description=data.description,
                resolution=data.resolution,
                status=DEFAULT_INCIDENT_CLOSE_FINAL_STATUS,
                status_reason=DEFAULT_INCIDENT_CLOSE_STATUS_REASON,
            )
            await self._handler.client.update_incident(
                state.request_id,
                EntryValuesMapper.wrap_entry_body(close_values),
            )
            logger.info("close_incident ok incident_number=%s", data.incident_number)
            return BaseOutput(success=True, message=f"Incidente {data.incident_number} cerrado.")

        return await self._guarded_write(
            data.incident_number,
            close_flow,
            extra_guard=lambda state: require_submitter(state.submitter, self._handler.settings.username),
        )
