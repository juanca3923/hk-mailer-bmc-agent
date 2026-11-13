"""Pieces shared by the incident and work order tools."""

from collections.abc import Awaitable, Callable

from pydantic import BaseModel

from exception.mcp import MCPClientError
from services.bmc.tool_handler import BaseToolHandler
from type_defs.models.bmc.ar_api import ArScalarValue, BmcEntryListResponse
from type_defs.models.bmc.outputs import BaseOutput


async def search_detail_json(
    search: Awaitable[BmcEntryListResponse],
    *,
    not_found_message: str,
    build_detail: Callable[[dict[str, ArScalarValue]], BaseModel],
) -> str:
    """Await a ticket search and return its first entry as the tool's JSON answer.

    Parameters
    ----------
    search : Awaitable[BmcEntryListResponse]
        Pending search call (for example ``client.search_incident(number)``).
    not_found_message : str
        Error message when the search returns no entries.
    build_detail : Callable[[dict[str, ArScalarValue]], BaseModel]
        Builds the lean detail model from the raw values of the first entry.

    Returns
    -------
    str
        JSON ``BaseOutput``: TOON-encoded detail on success, otherwise the failure message.
    """
    try:
        result = await search
    except MCPClientError as exc:
        return BaseToolHandler.failure(exc).model_dump_json()
    first = result.first_values()
    if first is None:
        return BaseOutput(success=False, message=not_found_message).model_dump_json()
    return BaseToolHandler.success_toon(build_detail(first.data)).model_dump_json()


def work_log_options(note_text: str, work_log_type: str, view_access: str, secure_work_log: str) -> dict[str, str]:
    """Group the note arguments of a tool call as keyword arguments for the note input models.

    Parameters
    ----------
    note_text : str
        Work log detailed description text.
    work_log_type : str
        Category of the note in the activity log.
    view_access : str
        Visibility of the note in BMC.
    secure_work_log : str
        Whether the note is flagged as secure.

    Returns
    -------
    dict[str, str]
        The same four values keyed by field name.
    """
    return {
        'note_text': note_text,
        'work_log_type': work_log_type,
        'view_access': view_access,
        'secure_work_log': secure_work_log,
    }
