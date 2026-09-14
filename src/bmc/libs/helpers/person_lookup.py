"""Resolve a ticket reporter's real identity (First/Last Name) via BMC's CTM:People.

BMC's create forms have no "create from just an email" field: ``First Name``/
``Last Name`` (submitter identity, distinct from the fixed ``Customer`` identity)
must be sent as free text. To attribute a ticket to the actual person who reported
it — instead of this agent's own service-account persona — this looks up their
email in ``CTM:People`` first and fails closed (no ticket is created) when no
person can be confidently identified.
"""

from __future__ import annotations

import logging
from typing import NamedTuple

from bmc.exceptions.mcp import MCPClientError
from bmc.libs.api_client import BmcClient
from bmc.libs.constants import (
    AR_FIELD_PEOPLE_FIRST_NAME,
    AR_FIELD_PEOPLE_LAST_NAME,
    AR_FIELD_PEOPLE_LOGIN_ID,
    USER_ERROR_MESSAGE_PERSON_NOT_FOUND,
)
from bmc.type_defs.ar_api import BmcEntryValues
from bmc.type_defs.outputs import BaseOutput

logger = logging.getLogger(__name__)


class ReporterIdentity(NamedTuple):
    """First/Last Name resolved from a single ``CTM:People`` match."""

    first_name: str
    last_name: str


def _pick_entry(candidates: list[BmcEntryValues], email: str) -> BmcEntryValues:
    """Disambiguate multiple ``CTM:People`` matches for the same email.

    ``Internet E-mail`` is not a unique key in BMC: a service-account/bot People
    record can share it with a real person's record (observed in practice — this
    agent's own bot identity turned up as one of the matches for a real person's
    alternate email). When more than one entry comes back, prefer the one whose
    ``Remedy Login ID`` looks like a real login (contains ``@``) over a bot-style
    id such as ``AgentesIA``.

    **Ambiguous fallback**: if zero or more than one candidate qualify as
    "email-shaped", this returns the first entry BMC returned. BMC's result order
    for a non-unique qualification is not guaranteed by the API, so this fallback
    can end up picking the wrong person (or the bot itself) — it exists only so
    ticket creation does not hang on an unresolvable case, not because the choice
    is reliable. It is logged at WARNING specifically so a wrong attribution can be
    traced back to this ambiguity later instead of looking like a silent bug.
    """
    if len(candidates) == 1:
        return candidates[0]
    email_shaped = [c for c in candidates if '@' in c.get_str(AR_FIELD_PEOPLE_LOGIN_ID)]
    if len(email_shaped) == 1:
        return email_shaped[0]
    logger.warning(
        'resolve_reporter_identity: %d coincidencias en CTM:People para %r, ninguna o '
        'varias con Remedy Login ID con forma de correo; se usa la primera devuelta por '
        'BMC (orden no garantizado por la API) — la identidad asignada puede ser incorrecta',
        len(candidates),
        email,
    )
    return candidates[0]


async def resolve_reporter_identity(client: BmcClient, email: str) -> ReporterIdentity | BaseOutput:
    """Look up First/Last Name in ``CTM:People`` for the person creating a ticket.

    Parameters
    ----------
    client : BmcClient
        BMC HTTP client.
    email : str
        Reporter's email address, matched against ``Internet E-mail``.

    Returns
    -------
    ReporterIdentity | BaseOutput
        The resolved identity on success; a ``success=False`` ``BaseOutput`` when
        no person is found, the matched record has incomplete name data, or the
        lookup itself fails — the caller should return that output as-is and must
        not proceed to create the ticket.
    """
    normalized_email = email.strip()
    try:
        search = await client.search_person_by_email(normalized_email)
    except MCPClientError as exc:
        return BaseOutput(success=False, message=exc.message)
    if not search.entries:
        return BaseOutput(
            success=False,
            message=USER_ERROR_MESSAGE_PERSON_NOT_FOUND.format(email=normalized_email),
        )
    chosen = _pick_entry([entry.values for entry in search.entries], normalized_email)
    first_name = chosen.get_str(AR_FIELD_PEOPLE_FIRST_NAME)
    last_name = chosen.get_str(AR_FIELD_PEOPLE_LAST_NAME)
    if not first_name or not last_name:
        return BaseOutput(
            success=False,
            message=USER_ERROR_MESSAGE_PERSON_NOT_FOUND.format(email=normalized_email),
        )
    return ReporterIdentity(first_name=first_name, last_name=last_name)
