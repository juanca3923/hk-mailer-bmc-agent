"""Descriptions shown to the LLM for BMC tools that share the same wording."""

from typing import Final

LIST_BY_EMAIL_DESCRIPTION: Final[str] = (
    'List {ticket_kind} for one person, searched by the email they used as '
    'reporter_email at creation — not their BMC-resolved login id. One row per '
    'ticket: title, status and assigned group only; capped and flagged if there '
    'are more matches than returned.'
)
