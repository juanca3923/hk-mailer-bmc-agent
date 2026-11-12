"""Startup self-check: confirm BMC knows the ``CTM:People`` status field the sender verification relies on.

``AR_FIELD_PEOPLE_STATUS`` (``Profile Status``) is not in BMC's public docs and has to be confirmed against the real
instance. A harmless lookup of a reserved-TLD address asks BMC for that field: if BMC rejects the request, the log
says so at startup instead of every sender silently looking disabled on the first real email.
"""

from __future__ import annotations

import asyncio
import logging

from bmc.exceptions.mcp import MCPClientError
from bmc.libs import tool_handler
from bmc.libs.api_client import BmcClient
from bmc.libs.constants import AR_FIELD_PEOPLE_STATUS

logger = logging.getLogger(__name__)

PREFLIGHT_TIMEOUT_SEC = 60.0
# Reserved TLD (RFC 2606): the check never looks up a real person.
DUMMY_ADDRESS = 'autochequeo@arranque.invalid'
HTTP_BAD_REQUEST = 400


def build_people_client() -> BmcClient:
    """Return the shared BMC client (built from ``BMC_*`` settings on first use)."""
    return tool_handler.get_shared_handler().client


async def check_people_status_field(client: BmcClient) -> bool:
    """Ask BMC for the people status field with a dummy address and log what it answers.

    Parameters
    ----------
    client : BmcClient
        BMC HTTP client.

    Returns
    -------
    bool
        ``True`` when BMC accepted the request (so the field name is valid); ``False`` otherwise.
    """
    try:
        await client.search_person_by_email(DUMMY_ADDRESS)
    except MCPClientError as exc:
        if exc.status_code == HTTP_BAD_REQUEST:
            logger.warning(
                'preflight: BMC rechazó la consulta de CTM:People con el campo de estado %r (%s). Confirma el '
                'nombre del campo en la instancia (GET de una persona sin fields) y corrige '
                'AR_FIELD_PEOPLE_STATUS en bmc/libs/constants.py; mientras tanto POST /people/verify no es fiable.',
                AR_FIELD_PEOPLE_STATUS,
                exc.message,
            )
        else:
            logger.warning(
                'preflight: no se pudo comprobar el campo de estado de CTM:People: %s (HTTP %s)',
                exc.message,
                exc.status_code,
            )
        return False
    logger.info('preflight: BMC acepta el campo de estado %r de CTM:People', AR_FIELD_PEOPLE_STATUS)
    return True


async def run_startup_preflight() -> None:
    """Run the check with a time limit; whatever happens, startup continues."""
    try:
        client = build_people_client()
        await asyncio.wait_for(check_people_status_field(client), PREFLIGHT_TIMEOUT_SEC)
    except TimeoutError:
        logger.warning('preflight: BMC tardó más de %s s en responder; se omite el autochequeo', PREFLIGHT_TIMEOUT_SEC)
    except ValueError as exc:  # pydantic.ValidationError (BMC_* mal configurado) es un ValueError
        logger.warning('preflight: no se pudo preparar el cliente de BMC: %s', exc)
