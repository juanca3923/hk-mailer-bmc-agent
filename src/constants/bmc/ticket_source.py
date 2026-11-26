"""How each ticket source is written in BMC's work order fields."""

from typing import Final

from type_defs.enums.ticket_source import TicketSource

# ``ReportedSource`` (UI "Fuente reportada") per source.
REPORTED_SOURCE_BY_SOURCE: Final[dict[TicketSource, str]] = {TicketSource.MAILER: 'Email'}

# ``AA_ResolutionMethod_WO`` (UI "Método de resolución") per source.
RESOLUTION_METHOD_BY_SOURCE: Final[dict[TicketSource, str]] = {TicketSource.MAILER: 'Correo'}
