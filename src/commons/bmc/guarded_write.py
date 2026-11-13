"""Shared skeleton of the guarded ticket writes (incidents and work orders)."""

from collections.abc import Awaitable, Callable
from typing import Protocol

from commons.bmc.ticket_guards import TicketState, require_not_closed
from exception.mcp import MCPClientError
from type_defs.models.bmc.inputs import WorkLogInput
from type_defs.models.bmc.outputs import BaseOutput


class WriteGate(Protocol):
    """Handler surface needed to check that writes are enabled."""

    def ensure_write_allowed(self) -> BaseOutput | None:
        """Return error output when writes are disabled."""


async def run_guarded_write(
    handler: WriteGate,
    *,
    resolve: Callable[[], Awaitable[tuple[TicketState | None, BaseOutput | None]]],
    missing_message: str,
    action: Callable[[TicketState], Awaitable[BaseOutput]],
    extra_guard: Callable[[TicketState], BaseOutput | None] | None = None,
) -> BaseOutput:
    """Run one write on a ticket after the common guards.

    Order: writes enabled (nothing is searched when they are not), ticket resolved, ticket not
    ``Closed``, optional ``extra_guard``; then ``action``. A BMC client error raised by ``action``
    becomes a failed output.

    Parameters
    ----------
    handler : WriteGate
        Tool handler; its ``ensure_write_allowed`` decides whether writes are enabled.
    resolve : Callable[[], Awaitable[tuple[TicketState | None, BaseOutput | None]]]
        Looks the ticket up. It is a callable so that nothing runs when writes are disabled.
    missing_message : str
        Error message when ``resolve`` returns neither a state nor an error.
    action : Callable[[TicketState], Awaitable[BaseOutput]]
        The BMC calls to perform; returns the success output.
    extra_guard : Callable[[TicketState], BaseOutput | None] | None, optional
        Additional rejection rule (for example ownership), checked after the closed-ticket guard.

    Returns
    -------
    BaseOutput
        The first guard rejection, the failed output of a BMC error, or the output of ``action``.
    """
    blocked = handler.ensure_write_allowed()
    if blocked is not None:
        return blocked

    state, error = await resolve()
    if error is not None or state is None:
        return error or BaseOutput(success=False, message=missing_message)

    rejection = require_not_closed(state.status)
    if rejection is None and extra_guard is not None:
        rejection = extra_guard(state)
    if rejection is not None:
        return rejection

    try:
        return await action(state)
    except MCPClientError as exc:
        return BaseOutput(success=False, message=exc.message)


def work_log_fields(data: WorkLogInput) -> dict[str, str]:
    """Return the work log fields of a note input as keyword arguments for the AR values models.

    Parameters
    ----------
    data : WorkLogInput
        Note input of an incident or a work order.

    Returns
    -------
    dict[str, str]
        ``work_log_type``, ``view_access``, ``secure_work_log`` and ``detailed_description``.
    """
    return {
        'work_log_type': data.work_log_type,
        'view_access': data.view_access,
        'secure_work_log': data.secure_work_log,
        'detailed_description': data.note_text,
    }
