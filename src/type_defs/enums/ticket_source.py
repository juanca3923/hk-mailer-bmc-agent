"""Systems that can ask this agent to create or close a ticket."""

from enum import StrEnum


class TicketSource(StrEnum):
    """Origin of a ticket request, declared by the caller in the ``Fuente:`` line of its message."""

    MAILER = 'mailer'
