"""Campos de un ticket leídos de una búsqueda para las guardas de escritura."""

from __future__ import annotations

from typing import NamedTuple


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
