"""Caracterización de las escrituras con guardas (incidentes y órdenes de trabajo).

Fijan el comportamiento observable de ``add_note``, ``add_attachment``, ``update_status`` y ``close``
(escritura deshabilitada, ticket inexistente, ticket cerrado, error de BMC y éxito) para poder
refactorizar el esqueleto común sin cambiar nada.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest

from commons.bmc.multipart_builder import AttachmentPart
from constants.bmc.fields import AR_FIELD_REQUEST_ID, AR_FIELD_STATUS, AR_FIELD_SUBMITTER
from constants.bmc.messages import (
    USER_ERROR_MESSAGE_INCIDENT_NOT_FOUND,
    USER_ERROR_MESSAGE_INCIDENT_REQUEST_ID_MISSING,
    USER_ERROR_MESSAGE_TICKET_ALREADY_CLOSED,
    USER_ERROR_MESSAGE_WORK_ORDER_NOT_FOUND,
    USER_ERROR_MESSAGE_WORK_ORDER_REQUEST_ID_MISSING,
    USER_ERROR_MESSAGE_WRITE_DISABLED,
)
from exception.mcp import MCPClientError
from services.bmc.incident_operations import IncidentOperations
from services.bmc.work_order_operations import WorkOrderOperations
from type_defs.models.bmc.ar_api import BmcEntry, BmcEntryListResponse, BmcEntryValues
from type_defs.models.bmc.inputs import (
    AddIncidentAttachmentInput,
    AddIncidentNoteInput,
    AddWorkOrderAttachmentInput,
    AddWorkOrderNoteInput,
    CloseIncidentInput,
    CloseWorkOrderInput,
    UpdateWorkOrderStatusInput,
)
from type_defs.models.bmc.outputs import BaseOutput

TICKET_ID = 'T1'
USERNAME = 'svc_mosaico'
BMC_DOWN = 'BMC caído'


class FakeSettings:
    username = USERNAME
    assignee_display_name = 'Mosaico WebServices'


class FakeClient:
    """Serves one ticket for both ticket types and records every write."""

    def __init__(self) -> None:
        self.status = 'In Progress'
        self.submitter = USERNAME
        self.request_id = 'REQ001'
        self.found = True
        self.write_error: MCPClientError | None = None
        self.searches = 0
        self.posts: list[object] = []
        self.updates: list[tuple[str, dict[str, Any]]] = []

    async def _search(self) -> BmcEntryListResponse:
        self.searches += 1
        if not self.found:
            return BmcEntryListResponse(entries=[])
        data = {AR_FIELD_REQUEST_ID: self.request_id, AR_FIELD_STATUS: self.status, AR_FIELD_SUBMITTER: self.submitter}
        return BmcEntryListResponse(entries=[BmcEntry(values=BmcEntryValues(data=data))])

    async def search_incident(self, _number: str) -> BmcEntryListResponse:
        return await self._search()

    async def search_work_order(self, _number: str) -> BmcEntryListResponse:
        return await self._search()

    async def _post(self, body: object) -> dict[str, Any]:
        if self.write_error is not None:
            raise self.write_error
        self.posts.append(body)
        return {}

    async def post_incident_work_log(self, body: object) -> dict[str, Any]:
        return await self._post(body)

    async def post_work_info(self, body: object) -> dict[str, Any]:
        return await self._post(body)

    async def _update(self, request_id: str, body: dict[str, Any]) -> dict[str, Any]:
        if self.write_error is not None:
            raise self.write_error
        self.updates.append((request_id, body))
        return {}

    async def update_incident(self, request_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return await self._update(request_id, body)

    async def update_work_order(self, request_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return await self._update(request_id, body)


class FakeHandler:
    """Stands in for ``BaseToolHandler``: configurable write switch and attachment loader."""

    def __init__(self, client: FakeClient, *, allow_write: bool = True) -> None:
        self.client = client
        self.settings = FakeSettings()
        self.allow_write = allow_write
        self.loaded: list[str] = []
        self.load_error: MCPClientError | None = None

    def ensure_write_allowed(self) -> BaseOutput | None:
        if self.allow_write:
            return None
        return BaseOutput(success=False, message=USER_ERROR_MESSAGE_WRITE_DISABLED)

    def load_attachment(self, file_path: str) -> AttachmentPart:
        if self.load_error is not None:
            raise self.load_error
        self.loaded.append(file_path)
        return AttachmentPart('evidencia.png', b'data', 'image/png')


@dataclass(frozen=True)
class Kind:
    """How to drive one ticket type through the common write operations."""

    name: str
    operations: Callable[[FakeHandler], Any]
    note_input: Callable[[], Any]
    attachment_input: Callable[[], Any]
    close_input: Callable[[], Any]
    not_found_message: str
    request_id_missing_message: str


INCIDENT = Kind(
    name='incident',
    operations=IncidentOperations,
    note_input=lambda: AddIncidentNoteInput(incident_number=TICKET_ID, note_text='nota'),
    attachment_input=lambda: AddIncidentAttachmentInput(incident_number=TICKET_ID, note_text='nota', file_path='f.png'),
    close_input=lambda: CloseIncidentInput(incident_number=TICKET_ID, description='cierre'),
    not_found_message=USER_ERROR_MESSAGE_INCIDENT_NOT_FOUND.format(incident_number=TICKET_ID),
    request_id_missing_message=USER_ERROR_MESSAGE_INCIDENT_REQUEST_ID_MISSING,
)
WORK_ORDER = Kind(
    name='work_order',
    operations=WorkOrderOperations,
    note_input=lambda: AddWorkOrderNoteInput(work_order_id=TICKET_ID, note_text='nota'),
    attachment_input=lambda: AddWorkOrderAttachmentInput(work_order_id=TICKET_ID, note_text='nota', file_path='f.png'),
    close_input=lambda: CloseWorkOrderInput(work_order_id=TICKET_ID),
    not_found_message=USER_ERROR_MESSAGE_WORK_ORDER_NOT_FOUND.format(work_order_id=TICKET_ID),
    request_id_missing_message=USER_ERROR_MESSAGE_WORK_ORDER_REQUEST_ID_MISSING,
)
KINDS = [pytest.param(INCIDENT, id='incident'), pytest.param(WORK_ORDER, id='work_order')]

# Operaciones comunes a ambos tipos: nombre del método y cómo construir su input.
COMMON_WRITES = ['add_note', 'add_attachment', 'close']


def _input(kind: Kind, operation: str) -> Any:
    builders = {'add_note': kind.note_input, 'add_attachment': kind.attachment_input, 'close': kind.close_input}
    return builders[operation]()


async def _run(kind: Kind, operation: str, handler: FakeHandler) -> BaseOutput:
    return await getattr(kind.operations(handler), operation)(_input(kind, operation))


def _writes(client: FakeClient) -> int:
    return len(client.posts) + len(client.updates)


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('operation', COMMON_WRITES)
async def test_disabled_writes_are_rejected_before_searching_the_ticket(kind: Kind, operation: str) -> None:
    client = FakeClient()
    handler = FakeHandler(client, allow_write=False)

    result = await _run(kind, operation, handler)

    assert (result.success, result.message) == (False, USER_ERROR_MESSAGE_WRITE_DISABLED)
    assert client.searches == 0
    assert _writes(client) == 0


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('operation', COMMON_WRITES)
async def test_unknown_ticket_returns_the_not_found_message(kind: Kind, operation: str) -> None:
    client = FakeClient()
    client.found = False

    result = await _run(kind, operation, FakeHandler(client))

    assert (result.success, result.message) == (False, kind.not_found_message)
    assert _writes(client) == 0


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('operation', COMMON_WRITES)
async def test_ticket_without_request_id_returns_the_missing_id_message(kind: Kind, operation: str) -> None:
    client = FakeClient()
    client.request_id = ''

    result = await _run(kind, operation, FakeHandler(client))

    assert (result.success, result.message) == (False, kind.request_id_missing_message)
    assert _writes(client) == 0


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('operation', COMMON_WRITES)
async def test_closed_ticket_is_rejected_without_writing(kind: Kind, operation: str) -> None:
    client = FakeClient()
    client.status = 'Closed'

    result = await _run(kind, operation, FakeHandler(client))

    assert (result.success, result.message) == (False, USER_ERROR_MESSAGE_TICKET_ALREADY_CLOSED)
    assert _writes(client) == 0


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('operation', COMMON_WRITES)
async def test_bmc_error_is_returned_as_a_failed_output(kind: Kind, operation: str) -> None:
    client = FakeClient()
    client.write_error = MCPClientError(BMC_DOWN)

    result = await _run(kind, operation, FakeHandler(client))

    assert (result.success, result.message) == (False, BMC_DOWN)


@pytest.mark.parametrize('kind', KINDS)
async def test_add_note_posts_one_work_log_and_confirms(kind: Kind) -> None:
    client = FakeClient()

    result = await _run(kind, 'add_note', FakeHandler(client))

    assert (result.success, result.message) == (True, f'Nota añadida a {TICKET_ID}.')
    assert len(client.posts) == 1
    assert client.updates == []


@pytest.mark.parametrize('kind', KINDS)
async def test_add_attachment_loads_the_file_posts_one_work_log_and_confirms(kind: Kind) -> None:
    client = FakeClient()
    handler = FakeHandler(client)

    result = await _run(kind, 'add_attachment', handler)

    assert (result.success, result.message) == (True, f'Adjunto añadido a {TICKET_ID}.')
    assert handler.loaded == ['f.png']
    assert len(client.posts) == 1


@pytest.mark.parametrize('kind', KINDS)
async def test_add_attachment_does_not_touch_the_disk_when_the_ticket_is_closed(kind: Kind) -> None:
    client = FakeClient()
    client.status = 'Closed'
    handler = FakeHandler(client)

    await _run(kind, 'add_attachment', handler)

    assert handler.loaded == []


@pytest.mark.parametrize('kind', KINDS)
async def test_add_attachment_load_failure_is_returned_without_posting(kind: Kind) -> None:
    client = FakeClient()
    handler = FakeHandler(client)
    handler.load_error = MCPClientError('ruta no permitida')

    result = await _run(kind, 'add_attachment', handler)

    assert (result.success, result.message) == (False, 'ruta no permitida')
    assert client.posts == []


@pytest.mark.parametrize('kind', KINDS)
async def test_close_by_another_submitter_is_rejected_without_writing(kind: Kind) -> None:
    client = FakeClient()
    client.submitter = 'otro_usuario'

    result = await _run(kind, 'close', FakeHandler(client))

    assert result.success is False
    assert 'otro_usuario' in result.message
    assert _writes(client) == 0


async def test_update_status_confirms_and_puts_once() -> None:
    client = FakeClient()
    data = UpdateWorkOrderStatusInput(work_order_id=TICKET_ID, description='avance', status='Planning')

    result = await WorkOrderOperations(FakeHandler(client)).update_status(data)

    assert (result.success, result.message) == (True, f'Estado actualizado para {TICKET_ID}.')
    assert [request_id for request_id, _ in client.updates] == ['REQ001']


async def test_update_status_rejects_disabled_writes_without_searching() -> None:
    client = FakeClient()
    data = UpdateWorkOrderStatusInput(work_order_id=TICKET_ID, description='avance', status='Planning')

    result = await WorkOrderOperations(FakeHandler(client, allow_write=False)).update_status(data)

    assert (result.success, result.message) == (False, USER_ERROR_MESSAGE_WRITE_DISABLED)
    assert client.searches == 0


async def test_update_status_returns_a_bmc_error_as_a_failed_output() -> None:
    client = FakeClient()
    client.write_error = MCPClientError(BMC_DOWN)
    data = UpdateWorkOrderStatusInput(work_order_id=TICKET_ID, description='avance', status='Planning')

    result = await WorkOrderOperations(FakeHandler(client)).update_status(data)

    assert (result.success, result.message) == (False, BMC_DOWN)
