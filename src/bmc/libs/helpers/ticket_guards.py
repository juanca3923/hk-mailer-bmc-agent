"""Pure business-rule guards for ticket write operations (status and ownership)."""

from typing import NamedTuple

from bmc.libs.constants import (
    TICKET_STATUS_CLOSED,
    USER_ERROR_MESSAGE_CLOSE_NOT_OWNER,
    USER_ERROR_MESSAGE_TICKET_ALREADY_CLOSED,
)
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
