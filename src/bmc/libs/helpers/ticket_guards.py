"""Pure business-rule guards for ticket write operations (status and ownership)."""

from collections.abc import Awaitable
from typing import NamedTuple

from bmc.exceptions.mcp import MCPClientError
from bmc.libs.constants import (
    AR_FIELD_REQUEST_ID,
    AR_FIELD_STATUS,
    AR_FIELD_SUBMITTER,
    TICKET_STATUS_CLOSED,
    USER_ERROR_MESSAGE_CLOSE_NOT_OWNER,
    USER_ERROR_MESSAGE_TICKET_ALREADY_CLOSED,
)
from bmc.type_defs.ar_api import BmcEntryListResponse
from bmc.type_defs.outputs import BaseOutput


class TicketState(NamedTuple):
    """Fields read from a ticket search needed by the write guards.

    Attributes
    ----------
    request_id : str
        AR Request ID used for subsequent PUTs.
    status : str
        Current ``Status`` value.
    submitter : str
        Current ``Submitter`` value (who opened the ticket in BMC).
    """

    request_id: str
    status: str
    submitter: str


def require_not_closed(status: str) -> BaseOutput | None:
    """Reject any write when the ticket is already ``Closed``.

    Parameters
    ----------
    status : str
        Current ``Status`` of the ticket.

    Returns
    -------
    BaseOutput | None
        Error output when *status* is ``Closed``; ``None`` otherwise.
    """
    if status == TICKET_STATUS_CLOSED:
        return BaseOutput(success=False, message=USER_ERROR_MESSAGE_TICKET_ALREADY_CLOSED)
    return None


def require_submitter(submitter: str, expected_username: str) -> BaseOutput | None:
    """Reject closing a ticket unless it was opened by the agent's own BMC user.

    Parameters
    ----------
    submitter : str
        Current ``Submitter`` of the ticket.
    expected_username : str
        Configured BMC service-account username (``BmcSettings.username``).

    Returns
    -------
    BaseOutput | None
        Error output when *submitter* does not match *expected_username*; ``None`` otherwise.
    """
    if submitter != expected_username:
        message = USER_ERROR_MESSAGE_CLOSE_NOT_OWNER.format(submitter=submitter)
        return BaseOutput(success=False, message=message)
    return None


async def resolve_ticket_state_from_search(
    search: Awaitable[BmcEntryListResponse],
    *,
    not_found_message: str,
    request_id_missing_message: str,
) -> tuple[TicketState | None, BaseOutput | None]:
    """Look up Request ID, Status, and Submitter from a pending ticket search.

    Shared by ``IncidentOperations.resolve_ticket_state`` and
    ``WorkOrderOperations.resolve_ticket_state``: both run this identical lookup —
    only the search call itself and the two error messages differ per ticket type.

    Parameters
    ----------
    search : Awaitable[BmcEntryListResponse]
        Pending search call (e.g. ``client.search_incident(incident_number)``),
        not yet awaited.
    not_found_message : str
        Error message when the search returns no entries.
    request_id_missing_message : str
        Error message when the matched entry has no ``Request ID``.

    Returns
    -------
    tuple[TicketState | None, BaseOutput | None]
        ``(state, None)`` on success; ``(None, error_output)`` on failure.
    """
    state: TicketState | None = None
    error: BaseOutput | None = None
    try:
        result = await search
        first = result.first_values()
        if first is None:
            error = BaseOutput(success=False, message=not_found_message)
        else:
            resolved = first.get_str(AR_FIELD_REQUEST_ID)
            if resolved:
                state = TicketState(
                    request_id=resolved,
                    status=first.get_str(AR_FIELD_STATUS),
                    submitter=first.get_str(AR_FIELD_SUBMITTER),
                )
            else:
                error = BaseOutput(success=False, message=request_id_missing_message)
    except MCPClientError as exc:
        error = BaseOutput(success=False, message=exc.message)
    return state, error
