"""Sender verification: lets another service check that an email belongs to an enabled BMC person."""

from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from config import get_logger
from exception.mcp import MCPClientError
from services.bmc import tool_handler
from services.bmc.person_lookup import verify_person_by_email
from type_defs.http.people import PersonVerifyRequest, PersonVerifyResponse

logger = get_logger()

router = APIRouter(prefix='/people', tags=['people'])


def require_verify_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    """Allow the call only with the shared key configured in ``BMC_VERIFY_API_KEY``.

    An empty configured key keeps the endpoint closed (503) instead of open, and the comparison is
    constant-time.

    Parameters
    ----------
    x_api_key : str | None
        Value of the ``X-API-Key`` header.

    Raises
    ------
    HTTPException
        503 when no key is configured; 401 when the header is missing or wrong.
    """
    expected = tool_handler.get_shared_handler().settings.verify_api_key
    if not expected:
        logger.error('people/verify: rejected, verify API key is not configured')
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail='Verificación de personas no configurada')
    if not x_api_key or not hmac.compare_digest(x_api_key.encode(), expected.encode()):
        logger.warning('people/verify: rejected, X-API-Key header %s', 'invalid' if x_api_key else 'missing')
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Clave inválida')


@router.post('/verify', response_model=PersonVerifyResponse, dependencies=[Depends(require_verify_key)])
async def verify_person(body: PersonVerifyRequest) -> PersonVerifyResponse:
    """Say whether an email exists in ``CTM:People`` and is enabled (nothing else about the person)."""
    handler = tool_handler.get_shared_handler()
    try:
        check = await verify_person_by_email(handler.client, body.email)
    except MCPClientError as exc:
        logger.error('people/verify: BMC lookup failed status=%s', exc.status_code)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail='No se pudo consultar BMC') from exc
    logger.info('people/verify: exists=%s enabled=%s', check.exists, check.enabled)
    return PersonVerifyResponse(exists=check.exists, enabled=check.enabled)
